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
from rgdps.constants.level_comments import LevelCommentSorting
from rgdps.constants.users import UserPrivileges
from rgdps.models.user import User
from rgdps.services import level_comments

PAGE_SIZE = 10


async def create_comment_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.COMMENTS_POST),
    ),
    level_id: int = Form(..., alias="levelID"),
    content: Base64String = Form(..., alias="comment"),
    percent: int = Form(default=0),
):
    # Allow users to run commands on levels.
    if commands.is_command(content):
        result_str = await commands.router.entrypoint(
            command=commands.strip_prefix(content),
            user=user,
            base_ctx=ctx,
            level_id=level_id,
            target_user_id=None,
        )

        return gd_obj.comment_ban_string(
            0,
            result_str,
        )

    comment = await level_comments.create(
        ctx,
        user_id=user.id,
        level_id=level_id,
        content=content,
        percent=percent,
    )

    if isinstance(comment, ServiceError):
        logger.info(
            "Failed to post level comment.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "content": content,
                "percent": percent,
                "error": comment.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully posted level comment.",
        extra={
            "comment_id": comment.id,
        },
    )
    return str(comment.id)


async def level_comments_get(
    ctx: HTTPContext = Depends(),
    level_id: int = Form(..., alias="levelID"),
    page: int = Form(...),
    page_size: int = Form(PAGE_SIZE, alias="count"),
    sort: LevelCommentSorting = Form(LevelCommentSorting.NEWEST, alias="mode"),
):
    result = await level_comments.get_level(
        ctx,
        level_id,
        page,
        page_size,
        sort,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to load level comments.",
            extra={
                "level_id": level_id,
                "page": page,
                "error": result.value,
            },
        )
        return responses.fail()

    response = "|".join(
        gd_obj.dumps(
            [
                gd_obj.create_level_comment(comment.comment, comment.user),
                gd_obj.create_level_comment_author(comment.user),
            ],
            sep="~",
        )
        for comment in result.comments
    )
    response += "#" + gd_obj.create_pagination_info(result.total, page, page_size)

    logger.info(
        "Successfully loaded level comments.",
        extra={
            "level_id": level_id,
            "page": page,
        },
    )
    return response


async def comment_history_get(
    ctx: HTTPContext = Depends(),
    user_id: int = Form(..., alias="userID"),
    page: int = Form(...),
    page_size: int = Form(PAGE_SIZE, alias="count"),
    sort: LevelCommentSorting = Form(LevelCommentSorting.NEWEST, alias="mode"),
):
    result = await level_comments.get_user(
        ctx,
        user_id,
        page,
        page_size,
        sort,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to load level comment history.",
            extra={
                "user_id": user_id,
                "page": page,
                "error": result.value,
            },
        )
        return responses.fail()

    response = "|".join(
        gd_obj.dumps(
            [
                gd_obj.create_level_comment(
                    comment.comment,
                    comment.user,
                    include_level_id=True,
                ),
                gd_obj.create_level_comment_author(comment.user),
            ],
            sep="~",
        )
        for comment in result.comments
    )
    response += "#" + gd_obj.create_pagination_info(result.total, page, page_size)

    logger.info(
        "Successfully loaded level comment history.",
        extra={
            "user_id": user_id,
            "page": page,
        },
    )
    return response


async def level_comment_delete(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.COMMENTS_DELETE_OWN),
    ),
    comment_id: int = Form(..., alias="commentID"),
):
    can_delete_any = bool(user.privileges & UserPrivileges.COMMENTS_DELETE_OTHER)
    result = await level_comments.delete(
        ctx,
        user.id,
        comment_id,
        can_delete_any,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to delete level comment.",
            extra={
                "user_id": user.id,
                "comment_id": comment_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully deleted level comment.",
        extra={
            "user_id": user.id,
            "comment_id": comment_id,
        },
    )
    return responses.success()
