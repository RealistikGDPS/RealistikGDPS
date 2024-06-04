from __future__ import annotations

import logging
from rgdps.common.context import Context
from rgdps.services.pubsub import RedisPubsubRouter
from rgdps.usecases import leaderboards
from rgdps.usecases import levels
from rgdps.usecases import users

router = RedisPubsubRouter()

# TODO: Look into creating unique UUIDs for each pubsub message,
# for easier identification in logging.


@router.register("rgdps:ping")
async def ping_handler(ctx: Context, data: bytes) -> None:
    logging.debug(
        "Redis received a ping.",
        extra={
            "data": data,
        },
    )


@router.register("rgdps:levels:sync_meili")
async def level_sync_meili_handler(ctx: Context, _) -> None:
    logging.debug("Redis received a level sync request.")
    await levels.synchronise_search(ctx)


@router.register("rgdps:users:sync_meili")
async def user_sync_meili_handler(ctx: Context, _) -> None:
    logging.debug("Redis received a user sync request.")
    await users.synchronise_search(ctx)


@router.register("rgdps:leaderboards:sync_stars")
async def leaderboard_sync_stars_handler(ctx: Context, _) -> None:
    logging.debug("Redis received a leaderboard sync request.")
    await leaderboards.synchronise_top_stars(ctx)


@router.register("rgdps:leaderboards:sync_creators")
async def leaderboard_sync_creators_handler(ctx: Context, _) -> None:
    logging.debug("Redis received a leaderboard sync request.")
    await leaderboards.synchronise_top_creators(ctx)
