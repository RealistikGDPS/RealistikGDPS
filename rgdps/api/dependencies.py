from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import Depends
from fastapi import Form
from fastapi.exceptions import HTTPException

from rgdps import logger
from rgdps import services
from rgdps.api.context import HTTPContext
from rgdps.constants.errors import ServiceError
from rgdps.constants.responses import GenericResponse
from rgdps.constants.users import UserPrivileges
from rgdps.models.user import User


# TODO: add option to replicate https://github.com/RealistikDash/GDPyS/blob/9266cc57c3a4c5d1f51363aa3899ee3c09a23ee8/web/http.py#L338-L341
def authenticate_dependency(
    user_id_alias: str = "accountID",
    password_alias: str = "gjp2",
    required_privileges: UserPrivileges | None = None,
) -> Callable[[HTTPContext, int, str], Awaitable[User]]:
    async def wrapper(
        ctx: HTTPContext = Depends(),
        user_id: int = Form(..., alias=user_id_alias),
        # A gjp2 is a hash thats always 40 characters long.
        gjp: str = Form(..., alias=password_alias, min_length=40, max_length=40),
    ) -> User:
        user = await services.user_credentials.authenticate_from_gjp2(
            ctx,
            user_id,
            gjp,
        )

        if isinstance(user, ServiceError):
            logger.debug(
                "Authentication failed for user.",
                extra={
                    "user_id": user_id,
                    "error": user.value,
                },
            )
            raise HTTPException(
                status_code=200,
                detail=str(GenericResponse.FAIL),
            )

        if required_privileges is not None and not (
            user.privileges & required_privileges == required_privileges
        ):
            logger.debug(
                "Authentication failed for user due to insufficient privileges.",
                extra={
                    "user_id": user_id,
                    "privileges": user.privileges,
                    "required_privileges": required_privileges,
                },
            )
            raise HTTPException(
                status_code=200,
                detail=str(GenericResponse.FAIL),
            )

        return user

    return wrapper


def password_authenticate_dependency(
    username_alias: str = "userName",
    password_alias: str = "password",
    required_privileges: UserPrivileges | None = None,
) -> Callable[[HTTPContext, str, str], Awaitable[User]]:
    async def wrapper(
        ctx: HTTPContext = Depends(),
        username: str = Form(..., alias=username_alias),
        password_plain: str = Form(..., alias=password_alias),
    ) -> User:
        user = await services.user_credentials.authenticate_from_name_plain(
            ctx,
            username,
            password_plain,
        )

        if isinstance(user, ServiceError):
            logger.debug(
                "Authentication failed for user.",
                extra={
                    "username": username,
                    "error": user.value,
                },
            )
            raise HTTPException(
                status_code=200,
                detail=str(GenericResponse.FAIL),
            )

        if required_privileges is not None and not (
            user.privileges & required_privileges == required_privileges
        ):
            logger.debug(
                "Authentication failed for user due to insufficient privileges.",
                extra={
                    "username": username,
                    "privileges": user.privileges,
                    "required_privileges": required_privileges,
                },
            )
            raise HTTPException(
                status_code=200,
                detail=str(GenericResponse.FAIL),
            )

        return user

    return wrapper
