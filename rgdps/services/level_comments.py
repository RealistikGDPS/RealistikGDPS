from __future__ import annotations

from typing import NamedTuple

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.constants.level_comments import LevelCommentSorting
from rgdps.constants.users import UserPrivacySetting
from rgdps.models.level_comment import LevelComment
from rgdps.models.user import User


class LevelCommentResponse(NamedTuple):
    comment: LevelComment
    user: User


class PaginatedLevelCommentResponse(NamedTuple):
    comments: list[LevelCommentResponse]
    total: int


async def get_level(
    ctx: Context,
    level_id: int,
    page: int = 0,
    page_size: int = 10,
    sorting: LevelCommentSorting = LevelCommentSorting.NEWEST,
) -> PaginatedLevelCommentResponse | ServiceError:
    comments = await repositories.level_comment.from_level_id_paginated(
        ctx,
        level_id,
        page,
        page_size,
        include_deleted=False,
        sorting=sorting,
    )

    users = await repositories.user.multiple_from_id(
        ctx,
        [comment.user_id for comment in comments],
    )
    level_comment_responses = [
        LevelCommentResponse(comment, user) for comment, user in zip(comments, users)
    ]

    comment_count = await repositories.level_comment.get_count_from_level(
        ctx,
        level_id,
    )

    return PaginatedLevelCommentResponse(level_comment_responses, comment_count)


async def get_user(
    ctx: Context,
    user_id: int,
    page: int = 0,
    page_size: int = 10,
    sorting: LevelCommentSorting = LevelCommentSorting.NEWEST,
    # TODO: Friends
    viewing_user_id: int | None = None,
) -> PaginatedLevelCommentResponse | ServiceError:
    user = await repositories.user.from_id(ctx, user_id)

    if user is None:
        return ServiceError.USER_NOT_FOUND

    if user.comment_privacy is UserPrivacySetting.PRIVATE:
        return ServiceError.USER_COMMENTS_PRIVATE

    comments = await repositories.level_comment.from_user_id_paginated(
        ctx,
        user_id,
        page,
        page_size,
        include_deleted=False,
        sorting=sorting,
    )

    comment_count = await repositories.level_comment.get_count_from_user(
        ctx,
        user_id,
    )

    return PaginatedLevelCommentResponse(
        [LevelCommentResponse(comment, user) for comment in comments],
        comment_count,
    )


async def create(
    ctx: Context,
    user_id: int,
    level_id: int,
    content: str,
    percent: int,
) -> LevelComment | ServiceError:
    # TODO: Spam protection
    level = await repositories.level.from_id(ctx, level_id=level_id)
    if level is None:
        return ServiceError.COMMENTS_TARGET_NOT_FOUND

    return await repositories.level_comment.create(
        ctx,
        user_id=user_id,
        level_id=level_id,
        content=content,
        percent=percent,
    )


async def delete(
    ctx: Context,
    user_id: int,
    comment_id: int,
    can_delete_any: bool,
) -> LevelComment | ServiceError:
    comment = await repositories.level_comment.from_id(ctx, comment_id)

    if comment is None:
        return ServiceError.COMMENTS_NOT_FOUND

    if comment.user_id != user_id and not can_delete_any:
        return ServiceError.COMMENTS_INVALID_OWNER

    comment = await repositories.level_comment.update_partial(
        ctx,
        comment_id,
        deleted=True,
    )

    if comment is None:
        return ServiceError.COMMENTS_NOT_FOUND

    return comment
