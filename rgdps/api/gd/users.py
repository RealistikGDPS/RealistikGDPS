from __future__ import annotations

from fastapi import Depends
from fastapi import Form
from pydantic import EmailStr

from rgdps import logger
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.api.dependencies import authenticate_dependency
from rgdps.common import gd_obj
from rgdps.api.validators import SocialMediaString
from rgdps.api.validators import TextBoxString
from rgdps.constants.errors import ServiceError
from rgdps.constants.responses import LoginResponse
from rgdps.constants.responses import RegisterResponse
from rgdps.constants.users import UserPrivacySetting
from rgdps.constants.users import UserPrivilegeLevel
from rgdps.constants.users import UserPrivileges
from rgdps.models.user import User
from rgdps.services import user_credentials
from rgdps.services import users

PAGE_SIZE = 10


async def register_post(
    ctx: HTTPContext = Depends(),
    username: TextBoxString = Form(..., alias="userName", min_length=3, max_length=15),
    email: EmailStr = Form(...),
    password: str = Form(..., min_length=6, max_length=20),
):
    result = await users.register(
        ctx,
        name=username,
        password=password,
        email=email,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "User registration failed.",
            extra={
                "username": username,
                "email": email,
                "error": result.value,
            },
        )
        match result.value:
            case ServiceError.USER_USERNAME_EXISTS:
                return responses.code(RegisterResponse.USERNAME_EXISTS)
            case ServiceError.USER_EMAIL_EXISTS:
                return responses.code(RegisterResponse.EMAIL_EXISTS)
            case _:
                return responses.fail()

    logger.info(
        "User registration success.",
        extra={
            "user_id": result.id,
            "username": username,
            "email": email,
        },
    )

    return responses.success()


async def login_post(
    ctx: HTTPContext = Depends(),
    username: TextBoxString = Form(..., alias="userName", max_length=15),
    gjp2: str = Form(..., max_length=40, min_length=40),
    # _: str = Form(..., alias="udid"),
):
    result = await user_credentials.authenticate_from_gjp2_name(ctx, username, gjp2)
    if isinstance(result, ServiceError):
        logger.info(
            "User login failed",
            extra={
                "username": username,
                "error": result.value,
            },
        )

        match result:
            case (
                ServiceError.AUTH_NOT_FOUND
                | ServiceError.USER_NOT_FOUND
                | ServiceError.AUTH_PASSWORD_MISMATCH
            ):
                return responses.code(LoginResponse.INVALID_CREDENTIALS)
            case ServiceError.AUTH_NO_PRIVILEGE | ServiceError.AUTH_UNSUPPORTED_VERSION:
                return responses.code(LoginResponse.ACCOUNT_DISABLED)
            case _:
                return responses.fail()

    logger.info(
        "User login successful!",
        extra={
            "user_id": result.id,
        },
    )

    return f"{result.id},{result.id}"


async def user_info_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
):
    is_own = target_id == user.id
    target = await users.get(ctx, user.id, target_id, is_own)

    if isinstance(target, ServiceError):
        logger.info(
            "Failed to view a profile.",
            extra={
                "error": target.value,
                "user_id": user.id,
                "target_id": target_id,
            },
        )
        return responses.fail()

    # TODO: Move to its own function.
    if (
        (not is_own)
        and (not target.user.privileges & UserPrivileges.USER_PROFILE_PUBLIC)
        and (not user.privileges & UserPrivileges.USER_VIEW_PRIVATE_PROFILE)
    ):
        logger.info(
            "Tried to view a profile with insufficient privileges.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully viewed a profile.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
        },
    )

    return gd_obj.dumps(
        [
            gd_obj.create_profile(
                target.user,
                target.friend_status,
                target.rank,
                target.messages_count,
                target.friend_request_count,
                target.friend_count,
            ),
            (
                gd_obj.create_friend_request(target.friend_request)
                if target.friend_request is not None
                else {}
            ),
        ],
    )


async def user_info_update(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    stars: int = Form(...),
    demons: int = Form(...),
    moons: int = Form(...),
    display_type: int = Form(..., alias="icon"),
    diamonds: int = Form(...),
    primary_colour: int = Form(..., alias="color1"),
    secondary_colour: int = Form(..., alias="color2"),
    glow_colour: int = Form(..., alias="color3"),
    icon: int = Form(..., alias="accIcon"),
    ship: int = Form(..., alias="accShip"),
    ball: int = Form(..., alias="accBall"),
    ufo: int = Form(..., alias="accBird"),
    wave: int = Form(..., alias="accDart"),
    robot: int = Form(..., alias="accRobot"),
    spider: int = Form(..., alias="accSpider"),
    swing_copter: int = Form(..., alias="accSwing"),
    jetpack: int = Form(..., alias="accJetpack"),
    glow: bool = Form(..., alias="accGlow"),
    explosion: int = Form(..., alias="accExplosion"),
    coins: int = Form(...),
    user_coins: int = Form(..., alias="userCoins"),
):
    res = await users.update_stats(
        ctx,
        user.id,
        stars=stars,
        demons=demons,
        moons=moons,
        display_type=display_type,
        diamonds=diamonds,
        primary_colour=primary_colour,
        secondary_colour=secondary_colour,
        glow_colour=glow_colour,
        icon=icon,
        ship=ship,
        ball=ball,
        ufo=ufo,
        wave=wave,
        robot=robot,
        swing_copter=swing_copter,
        jetpack=jetpack,
        spider=spider,
        glow=glow,
        explosion=explosion,
        coins=coins,
        user_coins=user_coins,
        update_rank=bool(user.privileges & UserPrivileges.USER_PROFILE_PUBLIC),
    )

    if isinstance(res, ServiceError):
        logger.info(
            "Failed to update the profile.",
            # XXX: Maybe add the stats here.
            extra={
                "error": res.value,
                "user_id": user.id,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully updated profile.",
        extra={
            "user_id": user.id,
        },
    )

    return str(user.id)


# NOTE: Comment Privacy is optional for now as some cleints don't send it. (2.111)
# Delete the default when 2.2 is released.
async def user_settings_update(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    youtube_name: SocialMediaString | None = Form(None, alias="yt"),
    twitter_name: SocialMediaString | None = Form(None, alias="twitter"),
    twitch_name: SocialMediaString | None = Form(None, alias="twitch"),
    message_privacy: UserPrivacySetting = Form(..., alias="mS"),
    friend_request_allowed: bool = Form(..., alias="frS"),
    comment_privacy: UserPrivacySetting = Form(UserPrivacySetting.PUBLIC, alias="cS"),
):
    friend_privacy = UserPrivacySetting.PUBLIC
    if not friend_request_allowed:
        friend_privacy = UserPrivacySetting.PRIVATE

    result = await users.update_user_settings(
        ctx,
        user.id,
        message_privacy=message_privacy,
        comment_privacy=comment_privacy,
        friend_privacy=friend_privacy,
        youtube_name=youtube_name,
        twitter_name=twitter_name,
        twitch_name=twitch_name,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to update user settings.",
            extra={
                "error": result.value,
                "user_id": user.id,
                "youtube_name": youtube_name,
                "twitter_name": twitter_name,
                "twitch_name": twitch_name,
                "message_privacy": message_privacy.name,
                "friend_privacy": friend_privacy.name,
                "comment_privacy": comment_privacy.name,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully updated user settings.",
        extra={
            "user_id": user.id,
            "youtube_name": youtube_name,
            "twitter_name": twitter_name,
            "twitch_name": twitch_name,
            "message_privacy": message_privacy.name,
            "friend_privacy": friend_privacy.name,
            "comment_privacy": comment_privacy.name,
        },
    )
    return responses.success()


async def request_status_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
):
    result = await users.request_status(ctx, user.id)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to get user request status.",
            extra={
                "error": result.value,
                "user_id": user.id,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully got user request status.",
        extra={
            "user_id": user.id,
            "status": result.name,
        },
    )

    if result is UserPrivilegeLevel.NONE:
        return responses.fail()

    return str(result)


async def users_get(
    ctx: HTTPContext = Depends(),
    query: str = Form("", alias="str"),
    page: int = Form(0),
):
    result = await users.search(ctx, page, PAGE_SIZE, query)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to search users.",
            extra={
                "query": query,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully searched users.",
        extra={
            "query": query,
            "results": result.total,
        },
    )

    # NOTE: Client shows garbage data if an empty list is sent.
    if not result.results:
        return responses.fail()

    return (
        "|".join(gd_obj.dumps(gd_obj.create_profile(user)) for user in result.results)
        + "#"
        + gd_obj.create_pagination_info(result.total, page, PAGE_SIZE)
    )
