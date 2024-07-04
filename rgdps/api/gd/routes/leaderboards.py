from __future__ import annotations

from fastapi import Depends
from fastapi import Form

from rgdps import logger
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.common import gd_obj
from rgdps.constants.errors import ServiceError
from rgdps.constants.leaderboards import LeaderboardType
from rgdps.services import leaderboards


async def leaderboard_get(
    ctx: HTTPContext = Depends(),
    leaderboard_type: LeaderboardType = Form(..., alias="type"),
):

    leaderboard = await leaderboards.get(ctx, leaderboard_type)

    if isinstance(leaderboard, ServiceError):
        logger.info(
            "Failed to load the leaderboard.",
            extra={
                "leaderboard_type": leaderboard_type.value,
                "error": leaderboard.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully fetched the leaderboard.",
        extra={
            "leaderboard_type": leaderboard_type.value,
        },
    )

    return "|".join(
        gd_obj.dumps(gd_obj.create_profile(user, rank=idx + 1))
        for idx, user in enumerate(leaderboard)
    )
