from __future__ import annotations

from fastapi import Depends
from fastapi import Form

from rgdps import logger
from rgdps.api import commands
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.api.dependencies import authenticate_dependency
from rgdps.common import gd_obj
from rgdps.api.validators import Base64String
from rgdps.constants.errors import ServiceError
from rgdps.constants.likes import LikeType
from rgdps.constants.users import UserPrivileges
from rgdps.models.user import User
from rgdps.services import likes
from rgdps.services import user_comments

PAGE_SIZE = 10


async def user_comments_get(
    target_id: int = Form(..., alias="accountID"),
    page: int = Form(..., alias="page"),
    ctx: HTTPContext = Depends(),
):
    result = await user_comments.get_user(
        ctx,
        target_id,
        page,
        PAGE_SIZE,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to view user comments.",
            extra={
                "error": result.value,
                "target_id": target_id,
                "page": page,
            },
        )
        return responses.fail()

    response = "|".join(
        gd_obj.dumps(gd_obj.create_user_comment(comment, result.user), sep="~")
        for comment in (result.comment)
    )
    response += "#" + gd_obj.create_pagination_info(result.total, page, PAGE_SIZE)

    logger.info(
        "Successfully viewed user comments.",
        extra={
            "target_id": target_id,
            "page": page,
        },
    )
    return response


async def user_comments_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(
            required_privileges=UserPrivileges.USER_CREATE_USER_COMMENTS,
        ),
    ),
    content: Base64String = Form(..., alias="comment", max_length=256),
):
    # Allow users to run commands on themselves.
    if commands.is_command(content):
        result_str = await commands.router.entrypoint(
            command=commands.strip_prefix(content),
            user=user,
            base_ctx=ctx,
            level_id=None,
            target_user_id=user.id,
        )

        # Comment bans allow you to show text to the user instead of posting the comment.
        return gd_obj.comment_ban_string(
            0,
            result_str,
        )

    result = await user_comments.create(ctx, user.id, content)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to post user comment.",
            extra={
                "error": result.value,
                "user_id": user.id,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully posted a user comment.",
        extra={
            "user_id": user.id,
            "comment_id": result.id,
        },
    )
    return responses.success()


# TODO: MOVE
async def like_target_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.COMMENTS_LIKE),
    ),
    target_type: LikeType = Form(..., alias="type"),
    target_id: int = Form(..., alias="itemID"),
    is_positive: bool = Form(..., alias="like"),
):

    # TODO: Move this logic to a single usecase.
    result = None
    if target_type is LikeType.USER_COMMENT:
        result = await likes.like_user_comment(
            ctx,
            user.id,
            target_id,
            int(is_positive),
        )
    elif target_type is LikeType.LEVEL:
        result = await likes.like_level(ctx, user.id, target_id, int(is_positive))

    else:
        raise NotImplementedError

    if isinstance(result, ServiceError):
        logger.info(
            f"Failed to like/dislike target.",
            extra={
                "user_id": user.id,
                "target_type": target_type.value,
                "target_id": target_id,
                "is_positive": is_positive,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully liked/disliked target.",
        extra={
            "like_id": result.id,
        },
    )
    return responses.success()


async def user_comment_delete(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    comment_id: int = Form(..., alias="commentID"),
):
    result = await user_comments.delete(ctx, user.id, comment_id)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to delete user comment.",
            extra={
                "user_id": user.id,
                "comment_id": comment_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully deleted comment.",
        extra={
            "user_id": user.id,
            "comment_id": comment_id,
        },
    )
    return responses.success()
