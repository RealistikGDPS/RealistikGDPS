from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.constants.users import UserPrivacySetting
from rgdps.constants.users import UserRelationshipType
from rgdps.models.message import Message
from rgdps.models.user import User


class MessageResponse(NamedTuple):
    message: Message
    user: User


class PaginatedMessagesResponse(NamedTuple):
    messages: list[MessageResponse]
    total: int


async def get(
    ctx: Context,
    user_id: int,
    message_id: int,
    include_deleted: bool = False,
) -> MessageResponse | ServiceError:
    message = await repositories.message.from_id(
        ctx,
        message_id=message_id,
        include_deleted=include_deleted,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    if message.sender_user_id != user_id and message.recipient_user_id != user_id:
        return ServiceError.MESSAGES_INVALID_OWNER

    if message.sender_user_id == user_id:
        recipient = await repositories.user.from_id(ctx, message.recipient_user_id)
    else:
        recipient = await repositories.user.from_id(ctx, message.sender_user_id)

    if recipient is None:
        return ServiceError.MESSAGES_INVALID_OWNER

    return MessageResponse(message=message, user=recipient)


async def get_sent(
    ctx: Context,
    user_id: int,
    page: int = 0,
    page_size: int = 10,
    include_deleted: bool = False,
) -> PaginatedMessagesResponse | ServiceError:
    messages = await repositories.message.from_recipient_user_id(
        ctx,
        recipient_user_id=user_id,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )

    users = await repositories.user.multiple_from_id(
        ctx,
        [message.sender_user_id for message in messages],
    )
    messages_resp = [
        MessageResponse(message, user) for message, user in zip(messages, users)
    ]

    messages_count = await repositories.message.from_recipient_user_id_count(
        ctx,
        recipient_user_id=user_id,
        include_deleted=include_deleted,
    )

    return PaginatedMessagesResponse(
        messages=messages_resp,
        total=messages_count,
    )


async def get_user(
    ctx: Context,
    user_id: int,
    page: int = 0,
    page_size: int = 10,
    include_deleted: bool = False,
) -> PaginatedMessagesResponse | ServiceError:
    messages = await repositories.message.from_sender_user_id(
        ctx,
        sender_user_id=user_id,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )

    users = await repositories.user.multiple_from_id(
        ctx,
        [message.recipient_user_id for message in messages],
    )
    messages_resp = [
        MessageResponse(message, user) for message, user in zip(messages, users)
    ]

    messages_count = await repositories.message.from_sender_user_id_count(
        ctx,
        sender_user_id=user_id,
        include_deleted=include_deleted,
    )

    return PaginatedMessagesResponse(
        messages=messages_resp,
        total=messages_count,
    )


async def create(
    ctx: Context,
    sender_user_id: int,
    recipient_user_id: int,
    subject: str,
    content: str,
) -> Message | ServiceError:

    if recipient_user_id == sender_user_id:
        return ServiceError.MESSAGES_INVALID_RECIPIENT

    recipient = await repositories.user.from_id(ctx, recipient_user_id)
    if recipient is None:
        return ServiceError.MESSAGES_INVALID_RECIPIENT

    friendship_check = await repositories.user_relationship.check_relationship_exists(
        ctx,
        user_id=sender_user_id,
        target_user_id=recipient_user_id,
        relationship_type=UserRelationshipType.FRIEND,
    )

    block_check = await repositories.user_relationship.check_relationship_exists(
        ctx,
        user_id=recipient_user_id,
        target_user_id=sender_user_id,
        relationship_type=UserRelationshipType.BLOCKED,
    )

    if block_check:
        return ServiceError.USER_BLOCKED_BY_USER

    if recipient.message_privacy is UserPrivacySetting.PRIVATE:
        return ServiceError.USER_MESSAGES_PRIVATE

    if recipient.message_privacy is UserPrivacySetting.FRIENDS and not friendship_check:
        return ServiceError.USER_NOT_FRIENDS

    message = await repositories.message.create(
        ctx,
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user_id,
        subject=subject,
        content=content,
    )

    return message


async def mark_message_as_seen(
    ctx: Context,
    user_id: int,
    message_id: int,
) -> Message | ServiceError:
    message = await repositories.message.from_id(
        ctx,
        message_id=message_id,
        include_deleted=False,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    if message.recipient_user_id != user_id:
        return ServiceError.MESSAGES_INVALID_RECIPIENT

    message = await repositories.message.update_partial(
        ctx,
        message_id=message_id,
        seen_ts=datetime.now(),
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    return message


async def delete_by_user(
    ctx: Context,
    user_id: int,
    message_id: int,
) -> Message | ServiceError:
    message = await repositories.message.from_id(
        ctx,
        message_id=message_id,
        include_deleted=False,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    if message.sender_user_id != user_id and message.recipient_user_id != user_id:
        return ServiceError.MESSAGES_INVALID_OWNER

    # Turns out that geometry dash delete message just for one person.
    sender_deleted = False
    recipient_deleted = False

    if message.sender_user_id == user_id:
        sender_deleted = True
    else:
        recipient_deleted = True

    message = await repositories.message.update_partial(
        ctx,
        message_id=message_id,
        sender_deleted=sender_deleted,
        recipient_deleted=recipient_deleted,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    return message


async def delete(
    ctx: Context,
    user_id: int,
    message_id: int,
) -> Message | ServiceError:
    message = await repositories.message.from_id(
        ctx,
        message_id=message_id,
        include_deleted=False,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    if message.sender_user_id != user_id and message.recipient_user_id != user_id:
        return ServiceError.MESSAGES_INVALID_OWNER

    message = await repositories.message.update_partial(
        ctx,
        message_id=message_id,
        deleted=True,
    )

    if message is None:
        return ServiceError.MESSAGES_NOT_FOUND

    return message
