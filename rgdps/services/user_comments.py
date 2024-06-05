from __future__ import annotations

from typing import NamedTuple

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.models.user import User
from rgdps.models.user_comment import UserComment


class UserCommentResponse(NamedTuple):
    comment: list[UserComment]
    user: User
    total: int


async def get_user(
    ctx: Context,
    user_id: int,
    page: int = 0,
    page_size: int = 10,
) -> UserCommentResponse | ServiceError:
    target_user = await repositories.user.from_id(ctx, user_id)

    if target_user is None:
        return ServiceError.USER_NOT_FOUND

    comments = await repositories.user_comment.from_user_id_paginated(
        ctx,
        user_id,
        page,
        page_size,
        include_deleted=False,
    )

    comment_count = await repositories.user_comment.get_user_comment_count(
        ctx,
        user_id,
    )

    return UserCommentResponse(comments, target_user, comment_count)


async def create(
    ctx: Context,
    user_id: int,
    content: str,
) -> UserComment | ServiceError:
    comment = await repositories.user_comment.create(
        ctx,
        user_id=user_id,
        content=content,
    )
    return comment


async def delete(
    ctx: Context,
    user_id: int,
    comment_id: int,
) -> UserComment | ServiceError:
    comment = await repositories.user_comment.from_id(ctx, comment_id)

    if comment is None:
        return ServiceError.COMMENTS_NOT_FOUND

    if comment.user_id != user_id:
        return ServiceError.COMMENTS_INVALID_OWNER

    comment = await repositories.user_comment.update_partial(
        ctx,
        comment_id=comment_id,
        deleted=True,
    )

    if comment is None:
        return ServiceError.COMMENTS_NOT_FOUND

    return comment
