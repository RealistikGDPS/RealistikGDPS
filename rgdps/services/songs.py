from __future__ import annotations

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.models.song import Song


async def get(ctx: Context, song_id: int) -> Song | ServiceError:
    song = await repositories.song.from_id(ctx, song_id)
    if song is None:
        # This could mean req fail too
        return ServiceError.SONGS_NOT_FOUND

    return song


async def get_custom_content_url(ctx: Context) -> str | ServiceError:
    url = await repositories.song.get_cdn_url(ctx)

    if url is None:
        return ServiceError.SONGS_CDN_UNAVAILABLE

    return url
