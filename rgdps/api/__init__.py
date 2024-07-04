from __future__ import annotations

import urllib.parse
import uuid

from databases import DatabaseURL
from fastapi import FastAPI
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis
from starlette.middleware.base import RequestResponseEndpoint

from rgdps import logger
from rgdps import settings
from rgdps.common.cache.memory import SimpleAsyncMemoryCache
from rgdps.common.cache.redis import SimpleRedisCache
from rgdps.constants.responses import GenericResponse
from rgdps.adapters.boomlings import GeometryDashClient
from rgdps.adapters.mysql import MySQLService
from rgdps.adapters.pubsub import listen_pubsubs
from rgdps.adapters.storage import LocalStorage
from rgdps.adapters.storage import S3Storage
from rgdps.adapters import MeiliSearchClient

from . import context
from . import gd
from . import pubsub


def init_logging() -> None:
    if settings.LOGZIO_ENABLED:
        logger.init_logzio_logging(
            settings.LOGZIO_TOKEN,
            settings.LOG_LEVEL,
            settings.LOGZIO_URL,
        )
    else:
        logger.init_basic_logging(settings.LOG_LEVEL)


def init_events(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_validation_error(
        request: Request,
        e: RequestValidationError,
    ) -> Response:
        logger.exception(
            f"A validation error has occured while parsing a request.",
            extra={
                "url": str(request.url),
                "method": request.method,
                "errors": e.errors(),
                "uuid": request.state.uuid,
            },
        )

        # If its a GD related request, give them something the client understands.
        if str(request.url).startswith(settings.APP_URL_PREFIX):
            return Response(str(GenericResponse.FAIL))

        return JSONResponse(
            {"message": "Validation error!"},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def init_mysql(app: FastAPI) -> None:
    database_url = DatabaseURL(
        "mysql+asyncmy://{username}:{password}@{host}:{port}/{db}".format(
            username=settings.SQL_USER,
            password=urllib.parse.quote(settings.SQL_PASS),
            host=settings.SQL_HOST,
            port=settings.SQL_PORT,
            db=settings.SQL_DB,
        ),
    )

    app.state.mysql = MySQLService(database_url)

    @app.on_event("startup")
    async def on_startup() -> None:
        await app.state.mysql.connect()
        logger.info(
            "Connected to the MySQL database.",
            extra={
                "host": settings.SQL_HOST,
                "db": settings.SQL_DB,
            },
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.mysql.disconnect()


def init_redis(app: FastAPI) -> None:
    app.state.redis = Redis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    )

    @app.on_event("startup")
    async def on_startup() -> None:
        await app.state.redis.initialize()
        shared_ctx = context.PubsubContext(app)
        await listen_pubsubs(
            shared_ctx,
            app.state.redis,
            pubsub.router,
        )

        # TODO: Custom ratelimit callback that returns `-1`.
        await FastAPILimiter.init(
            app.state.redis,
            prefix="rgdps:ratelimit",
        )

        logger.info(
            "Connected to the Redis database.",
            extra={
                "host": settings.REDIS_HOST,
                "db": settings.REDIS_DB,
            },
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.redis.close()


def init_meili(app: FastAPI) -> None:
    app.state.meili = MeiliSearchClient.from_host(
        settings.MEILI_HOST,
        settings.MEILI_PORT,
        settings.MEILI_KEY,
        timeout=10,
    )

    @app.on_event("startup")
    async def startup() -> None:
        await app.state.meili.health()
        logger.info(
            "Connected to the MeiliSearch database.",
            extra={
                "host": settings.MEILI_HOST,
            },
        )


def init_s3_storage(app: FastAPI) -> None:
    app.state.storage = S3Storage(
        region=settings.S3_REGION,
        endpoint=settings.S3_ENDPOINT,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        bucket=settings.S3_BUCKET,
        retries=10,
        timeout=5,
    )

    @app.on_event("startup")
    async def startup() -> None:
        app.state.storage = await app.state.storage.connect()
        logger.info(
            "Connected to S3 storage.",
            extra={
                "bucket": settings.S3_BUCKET,
                "region": settings.S3_REGION,
            },
        )

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await app.state.storage.disconnect()


def init_local_storage(app: FastAPI) -> None:
    app.state.storage = LocalStorage(
        root=settings.INTERNAL_RGDPS_DIRECTORY,
    )

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("Connected to the local storage.")


def init_gd(app: FastAPI) -> None:
    app.state.gd = GeometryDashClient(
        settings.SERVER_GD_URL,
    )

    logger.info(
        "Initialised the main Geometry Dash client.",
        extra={
            "server_url": settings.SERVER_GD_URL,
        },
    )


def init_cache(app: FastAPI) -> None:
    app.state.password_cache = SimpleAsyncMemoryCache()

    logger.info("Initialised stateful caching.")


def init_routers(app: FastAPI) -> None:
    import rgdps.api

    app.include_router(rgdps.api.gd.router)


def init_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def mysql_transaction(request: Request, call_next):
        logger.debug(
            "Opened a new MySQL transaction for request.",
            extra={
                "uuid": request.state.uuid,
            },
        )
        async with app.state.mysql.transaction() as sql:
            request.state.mysql = sql
            return await call_next(request)

    @app.middleware("http")
    async def enforce_user_agent(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Verifying request header for client endpoints.
        if str(request.url).startswith(settings.APP_URL_PREFIX):
            # GD sends an empty User-Agent header.
            user_agent = request.headers.get("User-Agent")
            if user_agent != "":
                logger.info(
                    "Client request stopped due to invalid User-Agent header.",
                    extra={
                        "url": str(request.url),
                        "uuid": request.state.uuid,
                        "user_agent": user_agent,
                    },
                )
                return Response(str(GenericResponse.FAIL))

        return await call_next(request)

    @app.middleware("http")
    async def exception_logging(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                f"An exception has occured while processing a request!",
                extra={
                    "url": str(request.url),
                    "method": request.method,
                    "uuid": request.state.uuid,
                },
            )
            raise e

    @app.middleware("http")
    async def assign_uuid(request: Request, call_next):
        request.state.uuid = str(uuid.uuid4())
        return await call_next(request)


def init_api() -> FastAPI:
    init_logging()
    app = FastAPI(
        title="RealistikGDPS",
        openapi_url=None,
        docs_url=None,
    )

    init_events(app)
    init_middlewares(app)
    init_mysql(app)
    init_redis(app)
    init_meili(app)
    init_gd(app)

    if settings.S3_ENABLED:
        init_s3_storage(app)
    else:
        init_local_storage(app)

    init_cache(app)

    init_routers(app)

    return app
