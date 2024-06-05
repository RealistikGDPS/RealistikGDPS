from fastapi import Depends
from fastapi import Form

from rgdps import logger
from rgdps.api import commands
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.api.dependencies import authenticate_dependency
from rgdps.common import gd_obj
from rgdps.api.validators import Base64String
from rgdps.api.validators import MessageContentString
from rgdps.constants.errors import ServiceError
from rgdps.constants.users import UserPrivileges
from rgdps.models.message import MessageDirection
from rgdps.models.user import User
from rgdps.services import messages

PAGE_SIZE = 10


async def message_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(
            required_privileges=UserPrivileges.MESSAGES_SEND,
        ),
    ),
    recipient_user_id: int = Form(..., alias="toAccountID"),
    subject: Base64String = Form(..., max_length=35),
    content: MessageContentString = Form(..., alias="body", max_length=200),
):
    # Commands hijack GD client requests to allow interaction directly through the client.
    if commands.is_command(content):
        return await commands.router.entrypoint(
            command=commands.strip_prefix(content),
            user=user,
            base_ctx=ctx,
            level_id=None,
            target_user_id=recipient_user_id,
        )

    message = await messages.create(
        ctx,
        sender_user_id=user.id,
        recipient_user_id=recipient_user_id,
        subject=subject,
        content=content,
    )

    if isinstance(message, ServiceError):
        logger.info(
            "Failed to send message.",
            extra={
                "sender_user_id": user.id,
                "recipient_user_id": recipient_user_id,
                "error": message.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully sent a message.",
        extra={
            "message_id": message.id,
        },
    )
    return responses.success()


async def messages_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    page: int = Form(0, alias="page"),
    is_sender_user_id: bool = Form(0, alias="getSent"),
):

    if is_sender_user_id:
        message_direction = MessageDirection.SENT
        result = await messages.get_user(
            ctx,
            user_id=user.id,
            page=page,
            page_size=PAGE_SIZE,
            include_deleted=False,
        )
    else:
        message_direction = MessageDirection.RECEIVED
        result = await messages.get_sent(
            ctx,
            user_id=user.id,
            page=page,
            page_size=PAGE_SIZE,
            include_deleted=False,
        )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to view message list.",
            extra={
                "user_id": user.id,
                "message_direction": message_direction.value,
                "error": result.value,
            },
        )
        return responses.fail()

    if not result.messages:
        return responses.code(-2)

    response = "|".join(
        gd_obj.dumps(
            gd_obj.create_message(
                message.message,
                message.user,
                message_direction=message_direction,
            ),
        )
        for message in result.messages
    )
    response += "#" + gd_obj.create_pagination_info(result.total, page, PAGE_SIZE)

    for message in result.messages:
        if not is_sender_user_id and message.message.seen_ts is None:
            await messages.mark_message_as_seen(ctx, user.id, message.message.id)

    logger.info(
        "Successfully viewed the messages list.",
        extra={
            "user_id": user.id,
            "message_direction": message_direction.value,
            "total": result.total,
        },
    )
    return response


# XXX: Untested because client doesn't seem to use this endpoint anymore.
# Added for completion.
async def message_get(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    message_id: int = Form(..., alias="messageID"),
):
    result = await messages.get(ctx, user.id, message_id=message_id)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to view message.",
            extra={
                "user_id": user.id,
                "message_id": message_id,
                "error": result.value,
            },
        )
        return responses.fail()

    if result.message.seen_ts is None:
        await messages.mark_message_as_seen(ctx, user.id, result.message.id)

    logger.info(
        "Successfully viewed message.",
        extra={
            "user_id": user.id,
            "message_id": message_id,
        },
    )
    return gd_obj.dumps(
        gd_obj.create_message(
            result.message,
            result.user,
            message_direction=MessageDirection.RECEIVED,
        ),
    )


async def message_delete(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(
            required_privileges=UserPrivileges.MESSAGES_DELETE_OWN,
        ),
    ),
    message_id: int = Form(0, alias="messageID"),
    message_id_list: str | None = Form(None, alias="messages"),
):
    if message_id_list:
        messages_list = [int(message) for message in message_id_list.split(",")]
    else:
        messages_list = [message_id]

    for message in messages_list:
        await messages.delete_by_user(ctx, user.id, message_id=message)

    logger.info(
        "Successfully deleted message(s).",
        extra={
            "user_id": user.id,
            "count": len(messages_list),
        },
    )
    return responses.success()
