from __future__ import annotations

from fastapi import Depends
from fastapi import Form

from rgdps import logger
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.api.dependencies import authenticate_dependency
from rgdps.common import gd_obj
from rgdps.api.validators import Base64String
from rgdps.constants.errors import ServiceError
from rgdps.constants.users import UserRelationshipType
from rgdps.models.user import User
from rgdps.services import friend_requests
from rgdps.services import user_relationships

PAGE_SIZE = 10


async def friend_requests_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    page: int = Form(..., alias="page"),
    is_sender_user_id: bool = Form(0, alias="getSent"),
):
    result = await friend_requests.get_user(
        ctx,
        user.id,
        page,
        PAGE_SIZE,
        is_sender_user_id=is_sender_user_id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to view friend request list.",
            extra={
                "user_id": user.id,
                "is_sender_user_id": is_sender_user_id,
                "error": result.value,
            },
        )
        return responses.fail()

    if not result.requests:  # No requests found.
        return responses.code(-2)

    response = "|".join(
        gd_obj.dumps(
            [
                gd_obj.create_friend_request(request.request),
                gd_obj.create_friend_request_author(request.user),
            ],
        )
        for request in result.requests
    )
    response += "#" + gd_obj.create_pagination_info(result.total, page, PAGE_SIZE)

    logger.info(
        "Successfully viewed friend requests list.",
        extra={
            "user_id": user.id,
            "is_sender_user_id": is_sender_user_id,
        },
    )
    return response


async def friend_request_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_user_id: int = Form(..., alias="toAccountID"),
    message: Base64String = Form("", alias="comment", max_length=140),
):
    result = await friend_requests.create(
        ctx,
        user.id,
        target_user_id,
        message,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to send a friend request.",
            extra={
                "user_id": user.id,
                "target_user_id": target_user_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully sent a friend request.",
        extra={
            "user_id": user.id,
            "target_user_id": target_user_id,
            "request_id": result.id,
        },
    )
    return responses.success()


async def friend_request_read(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    request_id: int = Form(..., alias="requestID"),
):
    result = await friend_requests.mark_as_seen(
        ctx,
        user.id,
        request_id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to mark friend request as seen.",
            extra={
                "user_id": user.id,
                "request_id": request_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully marked friend request as seen.",
        extra={
            "user_id": user.id,
            "request_id": result.id,
        },
    )
    return responses.success()


async def friend_requests_delete(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
    is_sender_user_id: bool = Form(0, alias="isSender"),
    accounts: str | None = Form(None, alias="accounts"),
):
    if accounts:
        accounts_list = [int(account) for account in accounts.split(",")]
    else:
        accounts_list = [target_id]

    result = await friend_requests.delete_multiple(
        ctx,
        user.id,
        accounts_list,
        is_sender_user_id=is_sender_user_id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to delete friend requests.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
                "is_sender_user_id": is_sender_user_id,
                "count": len(accounts_list),
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully deleted friend requests.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
            "is_sender_user_id": is_sender_user_id,
            "count": len(accounts_list),
        },
    )
    return responses.success()


async def friend_request_accept(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
    request_id: int = Form(..., alias="requestID"),
):
    result = await friend_requests.accept(
        ctx,
        sender_user_id=target_id,
        recipient_user_id=user.id,
        request_id=request_id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to accept friend request.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
                "request_id": request_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully accepted friend request.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
            "request_id": request_id,
        },
    )
    return responses.success()


async def user_relationships_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    relationship_type: UserRelationshipType = Form(..., alias="type"),
):
    result = await user_relationships.get_user(
        ctx,
        user.id,
        relationship_type,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to view relationships list.",
            extra={
                "user_id": user.id,
                "relationship_type": relationship_type.value,
                "error": result.value,
            },
        )
        return responses.fail()

    if not result.relationships:  # No relationships found.
        return responses.code(-2)

    response = "|".join(
        gd_obj.dumps(
            [
                gd_obj.create_profile(relationship.target_user),
                gd_obj.create_user_relationship(relationship.relationship),
            ],
        )
        for relationship in result.relationships
    )

    # Mark them as seen.
    await user_relationships.mark_all_as_seen(ctx, user.id, relationship_type)
    logger.info(
        "Successfully viewed relationship list.",
        extra={
            "user_id": user.id,
            "relationship_type": relationship_type.value,
            "count": len(result.relationships),
        },
    )

    return response


async def friend_remove_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
):
    result = await user_relationships.remove_friendship(
        ctx,
        user.id,
        target_id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to remove friend.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully removed friend.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
        },
    )
    return responses.success()


# TODO: Rewrite to be a single usecase.
async def block_user_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
):
    # TODO: Move to usecase
    result = await user_relationships.remove_friendship(
        ctx,
        user.id,
        target_id,
    )
    # TODO: Temp.
    if isinstance(result, ServiceError):
        logger.info(
            f"Failed remove friend.",
        )
        return responses.fail()

    result = await user_relationships.create(
        ctx,
        user.id,
        target_id,
        UserRelationshipType.BLOCKED,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to block user.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully blocked user.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
            "relationship_id": result.id,
        },
    )
    return responses.success()


async def unblock_user_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    target_id: int = Form(..., alias="targetAccountID"),
):
    result = await user_relationships.delete(
        ctx,
        user.id,
        target_id,
        UserRelationshipType.BLOCKED,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to unblock user.",
            extra={
                "user_id": user.id,
                "target_id": target_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully unblocked user.",
        extra={
            "user_id": user.id,
            "target_id": target_id,
        },
    )
    return responses.success()
