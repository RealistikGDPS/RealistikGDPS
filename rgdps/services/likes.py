from __future__ import annotations

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.constants.likes import LikeType
from rgdps.models.level import Level
from rgdps.models.user_comment import UserComment


async def like_user_comment(
    ctx: Context,
    user_id: int,
    comment_id: int,
    value: int = 1,
) -> UserComment | ServiceError:
    comment = await repositories.user_comment.from_id(ctx, comment_id)

    if comment is None:
        return ServiceError.LIKES_INVALID_TARGET

    if comment.user_id == user_id:
        return ServiceError.LIKES_OWN_TARGET

    if await repositories.like.exists_by_target_and_user(
        ctx,
        LikeType.USER_COMMENT,
        comment_id,
        user_id,
    ):
        return ServiceError.LIKES_ALREADY_LIKED

    await repositories.like.create(
        ctx,
        LikeType.USER_COMMENT,
        comment_id,
        user_id,
        value,
    )

    await repositories.user_comment.update_partial(
        ctx,
        comment_id,
        likes=comment.likes + value,
    )

    return comment


async def like_level(
    ctx: Context,
    user_id: int,
    comment_id: int,
    value: int = 1,
) -> Level | ServiceError:
    level = await repositories.level.from_id(ctx, comment_id)

    if level is None:
        return ServiceError.LIKES_INVALID_TARGET

    if level.user_id == user_id:
        return ServiceError.LIKES_OWN_TARGET

    if await repositories.like.exists_by_target_and_user(
        ctx,
        LikeType.USER_COMMENT,
        comment_id,
        user_id,
    ):
        return ServiceError.LIKES_ALREADY_LIKED

    if await repositories.like.exists_by_target_and_user(
        ctx,
        LikeType.USER_COMMENT,
        comment_id,
        user_id,
    ):
        return ServiceError.LIKES_ALREADY_LIKED

    await repositories.like.create(
        ctx,
        LikeType.LEVEL,
        level.id,
        user_id,
        value,
    )
    level = await repositories.level.update_partial(
        ctx,
        level.id,
        likes=level.likes + value,
    )

    if level is None:
        return ServiceError.LIKES_INVALID_TARGET

    return level
