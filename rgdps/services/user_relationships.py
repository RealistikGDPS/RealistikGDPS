from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.constants.users import UserRelationshipType
from rgdps.models.user import User
from rgdps.models.user_relationship import UserRelationship


class UserRelationshipResponse(NamedTuple):
    relationship: UserRelationship
    target_user: User


class PaginatedUserRelationshipResponse(NamedTuple):
    relationships: list[UserRelationshipResponse]
    total: int


async def get_user(
    ctx: Context,
    user_id: int,
    relationship_type: UserRelationshipType,
) -> PaginatedUserRelationshipResponse | ServiceError:
    relationships = await repositories.user_relationship.from_user_id(
        ctx,
        user_id,
        relationship_type,
        include_deleted=False,
    )

    users = await repositories.user.multiple_from_id(
        ctx,
        [relationship.target_user_id for relationship in relationships],
    )
    relationships_responses = [
        UserRelationshipResponse(relationship, user)
        for relationship, user in zip(relationships, users)
    ]

    relationship_count = (
        await repositories.user_relationship.get_user_relationship_count(
            ctx,
            user_id,
            relationship_type,
        )
    )

    return PaginatedUserRelationshipResponse(
        relationships_responses,
        relationship_count,
    )


async def mark_all_as_seen(
    ctx: Context,
    user_id: int,
    relationship_type: UserRelationshipType,
) -> ServiceError | None:
    seen_ts = datetime.utcnow()
    await repositories.user_relationship.mark_all_as_seen(
        ctx,
        user_id,
        relationship_type,
        seen_ts,
    )


async def create(
    ctx: Context,
    user_id: int,
    target_user_id: int,
    relationship_type: UserRelationshipType,
) -> UserRelationship | ServiceError:
    if user_id == target_user_id:
        return ServiceError.RELATIONSHIP_INVALID_TARGET_ID

    exists = await repositories.user_relationship.check_relationship_exists(
        ctx,
        user_id,
        target_user_id,
        relationship_type,
    )

    if exists:
        return ServiceError.RELATIONSHIP_EXISTS

    relationship = await repositories.user_relationship.create(
        ctx,
        user_id,
        target_user_id,
        relationship_type,
    )
    return relationship


async def remove_friendship(
    ctx: Context,
    user_id: int,
    target_user_id: int,
) -> ServiceError | None:
    if user_id == target_user_id:
        return ServiceError.RELATIONSHIP_INVALID_TARGET_ID

    relationship = await repositories.user_relationship.from_user_and_target_user(
        ctx,
        user_id,
        target_user_id,
        UserRelationshipType.FRIEND,
    )

    if relationship is None:
        return  # Doesn't matter if it doesn't exist.

    if relationship.user_id != user_id:
        return ServiceError.RELATIONSHIP_INVALID_OWNER

    relationship = await repositories.user_relationship.update_partial(
        ctx,
        relationship.id,
        deleted=True,
    )

    if relationship is None:
        return ServiceError.RELATIONSHIP_NOT_FOUND

    # Remove the other side of the relationship.
    relationship = await repositories.user_relationship.from_user_and_target_user(
        ctx,
        target_user_id,
        user_id,
        UserRelationshipType.FRIEND,
    )

    if relationship is None:
        return  # Doesn't matter if it doesn't exist.

    if relationship.user_id != target_user_id:
        return ServiceError.RELATIONSHIP_INVALID_OWNER

    relationship = await repositories.user_relationship.update_partial(
        ctx,
        relationship.id,
        deleted=True,
    )

    if relationship is None:
        return ServiceError.RELATIONSHIP_NOT_FOUND


async def delete(
    ctx: Context,
    user_id: int,
    target_user_id: int,
    relationship_type: UserRelationshipType,
) -> UserRelationship | ServiceError:
    relationship = await repositories.user_relationship.from_user_and_target_user(
        ctx,
        user_id,
        target_user_id,
        relationship_type,
    )

    if relationship is None:
        return ServiceError.RELATIONSHIP_NOT_FOUND

    if relationship.user_id != user_id:
        return ServiceError.RELATIONSHIP_INVALID_OWNER

    relationship = await repositories.user_relationship.update_partial(
        ctx,
        relationship.id,
        deleted=True,
    )

    if relationship is None:
        return ServiceError.RELATIONSHIP_NOT_FOUND

    return relationship
