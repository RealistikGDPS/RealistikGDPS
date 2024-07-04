from __future__ import annotations

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError


async def get(ctx: Context, user_id: int) -> str | ServiceError:
    """NOTE: This is memory expensive, with saves reasonably exceeding 200MB."""
    data = await repositories.save_data.from_user_id(ctx, user_id)

    if data is None:
        return ServiceError.SAVE_DATA_NOT_FOUND

    return data


async def save(
    ctx: Context,
    user_id: int,
    data: str,
    game_version: int,
    binary_version: int,
) -> None | ServiceError:
    # TODO: Data parsing

    # the 'a' are a placeholder for mappack strings and completed levels.
    # Unfortunately, afaik, they are only achievable through save data parsing
    # which I currently don't want to do.
    data += f";{game_version};{binary_version};a;a"

    await repositories.save_data.create(ctx, user_id, data)

    return None
