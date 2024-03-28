from __future__ import annotations

import urllib.parse
import uuid

import httpx
from databases import DatabaseURL
from fastapi import FastAPI
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi_limiter import FastAPILimiter
from meilisearch_python_sdk import AsyncClient as MeiliClient
from redis.asyncio import Redis
from starlette.middleware.base import RequestResponseEndpoint

from . import context
from . import gd
from . import pubsub
from . import responses
from rgdps import logger
from rgdps.common.cache.memory import SimpleAsyncMemoryCache
from rgdps.common.cache.redis import SimpleRedisCache
from rgdps.config import config
from rgdps.constants.responses import GenericResponse
from rgdps.services.mysql import MySQLService
from rgdps.services.pubsub import listen_pubsubs
from rgdps.services.storage import LocalStorage
from rgdps.services.storage import S3Storage


def init_logging() -> None:
    logger.init_basic_logging(config.log_level)


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
        if str(request.url).startswith(config.http_url_prefix):
            return Response(str(GenericResponse.FAIL))

        return JSONResponse(
            {"message": "Validation error!"},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def init_mysql(app: FastAPI) -> None:
    database_url = DatabaseURL(
        "mysql+asyncmy://{username}:{password}@{host}:{port}/{db}".format(
            username=config.sql_user,
            password=urllib.parse.quote(config.sql_pass),
            host=config.sql_host,
            port=config.sql_port,
            db=config.sql_db,
        ),
    )

    app.state.mysql = MySQLService(database_url)

    @app.on_event("startup")
    async def on_startup() -> None:
        await app.state.mysql.connect()
        logger.info(
            "Connected to the MySQL database.",
            extra={
                "host": config.sql_host,
                "db": config.sql_db,
            },
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.mysql.disconnect()


def init_redis(app: FastAPI) -> None:
    app.state.redis = Redis.from_url(
        f"redis://{config.redis_host}:{config.redis_port}/{config.redis_db}",
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
                "host": config.redis_host,
                "db": config.redis_db,
            },
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.redis.close()


def init_meili(app: FastAPI) -> None:
    app.state.meili = MeiliClient(
        f"http://{config.meili_host}:{config.meili_port}",
        config.meili_key,
        timeout=10,
    )

    @app.on_event("startup")
    async def startup() -> None:
        await app.state.meili.health()
        logger.info(
            "Connected to the MeiliSearch database.",
            extra={
                "host": config.meili_host,
            },
        )


def init_s3_storage(app: FastAPI) -> None:
    app.state.storage = S3Storage(
        region=config.s3_region,
        endpoint=config.s3_endpoint,
        access_key=config.s3_access_key,
        secret_key=config.s3_secret_key,
        bucket=config.s3_bucket,
        retries=10,
        timeout=5,
    )

    @app.on_event("startup")
    async def startup() -> None:
        app.state.storage = await app.state.storage.connect()
        logger.info(
            "Connected to S3 storage.",
            extra={
                "bucket": config.s3_bucket,
                "region": config.s3_region,
            },
        )

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await app.state.storage.disconnect()


def init_local_storage(app: FastAPI) -> None:
    app.state.storage = LocalStorage(
        root=config.local_root,
    )

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("Connected to the local storage.")


def init_http(app: FastAPI) -> None:
    app.state.http = httpx.AsyncClient()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await app.state.http.aclose()


def init_cache_stateful(app: FastAPI) -> None:
    app.state.user_cache = SimpleAsyncMemoryCache()
    app.state.password_cache = SimpleAsyncMemoryCache()

    logger.info("Initialised stateful caching.")


def init_cache_stateless(app: FastAPI) -> None:
    app.state.user_cache = SimpleRedisCache(
        redis=app.state.redis,
        key_prefix="rgdps:cache:user",
    )
    app.state.password_cache = SimpleRedisCache(
        redis=app.state.redis,
        key_prefix="rgdps:cache:password",
        deserialise=lambda x: x.decode(),
        serialise=lambda x: x.encode(),
    )

    logger.info("Initialised stateless caching.")


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
        if str(request.url).startswith(config.http_url_prefix):
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
    init_http(app)

    if config.s3_enabled:
        init_s3_storage(app)
    else:
        init_local_storage(app)

    if config.srv_stateless:
        init_cache_stateless(app)
    else:
        init_cache_stateful(app)

    init_routers(app)

    return app
