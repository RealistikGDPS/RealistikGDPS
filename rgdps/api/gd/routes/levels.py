from __future__ import annotations

from datetime import datetime

from fastapi import Depends
from fastapi import Form

from rgdps import logger
from rgdps.api import responses
from rgdps.api.context import HTTPContext
from rgdps.api.dependencies import authenticate_dependency
from rgdps.common import gd_obj
from rgdps.api.validators import Base64String
from rgdps.api.validators import CommaSeparatedIntList
from rgdps.api.validators import TextBoxString
from rgdps.constants.errors import ServiceError
from rgdps.constants.level_schedules import LevelScheduleType
from rgdps.constants.levels import LevelDemonRating
from rgdps.constants.levels import LevelLength
from rgdps.constants.levels import LevelSearchType
from rgdps.constants.levels import LevelFeature
from rgdps.constants.users import UserPrivileges
from rgdps.models.user import User
from rgdps.services import level_schedules
from rgdps.services import levels
from rgdps.services import songs

PAGE_SIZE = 10


async def song_info_get(
    ctx: HTTPContext = Depends(),
    song_id: int = Form(..., alias="songID"),
):
    song = await songs.get(ctx, song_id)
    if isinstance(song, ServiceError):
        logger.info(
            "Failed to fetch song.",
            extra={
                "song_id": song_id,
                "error": song.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully fetched song.",
        extra={
            "song_id": song_id,
        },
    )
    return gd_obj.dumps(gd_obj.create_song(song), sep="~|~")


DEFAULT_RENDER_STRING = "0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0_0"


async def level_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(authenticate_dependency()),
    level_id: int = Form(..., alias="levelID"),
    name: TextBoxString = Form(..., alias="levelName", max_length=32),
    custom_song_id: int = Form(..., alias="songID"),
    two_player: bool = Form(..., alias="twoPlayer"),
    object_count: int = Form(..., alias="objects"),
    coins: int = Form(...),
    unlisted: bool = Form(..., alias="unlisted"),
    render_str: str = Form(DEFAULT_RENDER_STRING, alias="extraString"),
    requested_stars: int = Form(..., alias="requestedStars", ge=0, le=10),
    level_data: str = Form(..., alias="levelString"),
    length: LevelLength = Form(..., alias="levelLength"),
    version: int = Form(..., alias="levelVersion"),
    description: Base64String = Form("", alias="levelDesc"),
    original: int = Form(..., alias="original"),
    official_song_id: int = Form(..., alias="audioTrack"),
    game_version: int = Form(..., alias="gameVersion"),
    binary_version: int = Form(..., alias="binaryVersion"),
    low_detail_mode: bool = Form(..., alias="ldm"),
    building_time: int = Form(..., alias="wt2"),
    song_ids: CommaSeparatedIntList = Form(CommaSeparatedIntList(), alias="songIDs"),
    sfx_ids: CommaSeparatedIntList = Form(CommaSeparatedIntList(), alias="sfxIDs"),
):

    level = await levels.create_or_update(
        ctx,
        user_id=user.id,
        level_id=level_id,
        name=name,
        custom_song_id=custom_song_id,
        two_player=two_player,
        object_count=object_count,
        coins=coins,
        unlisted=unlisted,
        render_str=render_str,
        requested_stars=requested_stars,
        level_data=level_data,
        length=length,
        version=version,
        description=description,
        original=original,
        official_song_id=official_song_id,
        game_version=game_version,
        binary_version=binary_version,
        low_detail_mode=low_detail_mode,
        building_time=building_time,
        song_ids=song_ids,
        sfx_ids=sfx_ids,
    )

    if isinstance(level, ServiceError):
        logger.info(
            "Failed to upload level.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "error": level.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully uploaded/updated level.",
        extra={
            "user_id": user.id,
            "level_id": level.id,
        },
    )
    return str(level.id)


async def levels_get(
    ctx: HTTPContext = Depends(),
    query: str = Form("", alias="str"),
    page: int = Form(0, alias="page", ge=0),
    search_type: LevelSearchType = Form(LevelSearchType.MOST_LIKED, alias="type"),
    level_lengths: str = Form(..., alias="len"),
    completed_levels: str | None = Form(None, alias="completedLevels"),
    featured: bool = Form(...),
    original: bool = Form(...),
    two_player: bool = Form(..., alias="twoPlayer"),
    unrated: bool = Form(False, alias="noStar"),
    rated: bool = Form(False, alias="star"),
    song_id: int | None = Form(None, alias="song"),
    custom_song_id: int | None = Form(None, alias="customSong"),
    followed_list: str | None = Form(None, alias="followed"),
):
    if level_lengths != "-":
        level_length_list = [
            LevelLength(x) for x in gd_obj.comma_separated_ints(level_lengths)
        ]
    else:
        level_length_list = None

    if completed_levels is not None:
        completed_levels_list = gd_obj.comma_separated_ints(completed_levels)
    else:
        completed_levels_list = None

    if followed_list is not None:
        followed_list_list = gd_obj.comma_separated_ints(followed_list)
    else:
        followed_list_list = None

    level_res = await levels.search(
        ctx,
        page=page,
        page_size=PAGE_SIZE,
        query=query,
        search_type=search_type,
        level_lengths=level_length_list,
        completed_levels=completed_levels_list,
        featured=featured,
        original=original,
        two_player=two_player,
        unrated=unrated,
        rated=rated,
        song_id=song_id,
        custom_song_id=custom_song_id,
        followed_list=followed_list_list,
    )

    if isinstance(level_res, ServiceError):
        logger.info(
            "Failed to search levels.",
            extra={
                "query": query,
                "page": page,
                "page_size": PAGE_SIZE,
                "search_type": search_type.value,
                "level_lengths": level_length_list,
                "featured": featured,
                "original": original,
                "two_player": two_player,
                "unrated": unrated,
                "rated": rated,
                "song_id": song_id,
                "custom_song_id": custom_song_id,
                "error": level_res.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully searched levels.",
        extra={
            "query": query,
            "page": page,
            "page_size": PAGE_SIZE,
            "search_type": search_type.value,
            "level_lengths": level_length_list,
            "featured": featured,
            "original": original,
            "two_player": two_player,
            "unrated": unrated,
            "rated": rated,
            "song_id": song_id,
            "custom_song_id": custom_song_id,
            "result_count": level_res.total,
        },
    )

    return "#".join(
        (
            "|".join(
                gd_obj.dumps(gd_obj.create_level_minimal(level))
                for level in level_res.levels
            ),
            "|".join(gd_obj.create_user_str(user) for user in level_res.users),
            "~:~".join(
                gd_obj.dumps(gd_obj.create_song(song), sep="~|~")
                for song in level_res.songs
            ),
            gd_obj.create_pagination_info(level_res.total, page, PAGE_SIZE),
            gd_obj.create_search_security_str(level_res.levels),
        ),
    )


async def level_get(
    ctx: HTTPContext = Depends(),
    level_id: int = Form(..., alias="levelID"),
):
    level_res = await levels.get(
        ctx,
        level_id,
        is_daily=level_id == -1,
        is_weekly=level_id == -2,
    )

    if isinstance(level_res, ServiceError):
        logger.info(
            "Failed to fetch level.",
            extra={
                "level_id": level_id,
                "error": level_res.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully fetched level.",
        extra={
            "level_id": level_res.level.id,
        },
    )

    return "#".join(
        (
            gd_obj.dumps(
                gd_obj.create_level(
                    level_res.level,
                    level_res.data,
                    level_res.schedule_id or 0,
                ),
            ),
            gd_obj.create_level_data_security_str(level_res.data),
            gd_obj.create_level_metadata_security_str_hashed(
                level_res.level,
                level_res.schedule_id or 0,
            ),
            gd_obj.create_level_metadata_security_str(
                level_res.level,
                level_res.schedule_id or 0,
            ),
        ),
    )


async def suggest_level_stars(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.LEVEL_RATE_STARS),
    ),
    level_id: int = Form(..., alias="levelID"),
    stars: int = Form(...),
    feature: LevelFeature = Form(...),
):
    result = await levels.suggest_stars(
        ctx,
        level_id=level_id,
        stars=stars,
        feature=feature,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to suggest stars.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "stars": stars,
                "feature": feature,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully suggested stars.",
        extra={
            "user_id": user.id,
            "level_id": level_id,
            "stars": stars,
            "feature": feature,
        },
    )

    return responses.success()


async def level_desc_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.LEVEL_UPDATE),
    ),
    level_id: int = Form(..., alias="levelID"),
    level_desc: Base64String = Form(..., alias="levelDesc"),
):
    result = await levels.set_description(
        ctx,
        level_id=level_id,
        user_id=user.id,
        description=level_desc,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to update description.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "level_desc": level_desc,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully updated description.",
        extra={
            "user_id": user.id,
            "level_id": level_id,
            "level_desc": level_desc,
        },
    )

    return responses.success()


async def level_delete_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.LEVEL_DELETE_OWN),
    ),
    level_id: int = Form(..., alias="levelID"),
):
    result = await levels.delete(
        ctx,
        level_id,
        user.id,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to delete level.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully deleted level.",
        extra={
            "user_id": user.id,
            "level_id": level_id,
        },
    )
    return responses.success()


# XXX: Should this be here?
async def daily_level_info_get(
    ctx: HTTPContext = Depends(),
    weekly: bool = Form(False),
):
    # This endpoint does not actually even give level info (not even a level id...)
    query_type = LevelScheduleType.WEEKLY if weekly else LevelScheduleType.DAILY

    result = await level_schedules.get_current(
        ctx,
        schedule_type=query_type,
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to fetch current level.",
            extra={
                "query_type": query_type.value,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully fetched current level.",
        extra={
            "query_type": query_type.value,
        },
    )

    time_remaining = (result.schedule.end_time - datetime.now()).seconds

    return f"{result.schedule.id}|{time_remaining}"


async def demon_difficulty_post(
    ctx: HTTPContext = Depends(),
    user: User = Depends(
        authenticate_dependency(required_privileges=UserPrivileges.LEVEL_RATE_STARS),
    ),
    level_id: int = Form(..., alias="levelID"),
    demon_difficulty: LevelDemonRating = Form(..., alias="rating"),
):
    result = await levels.set_demon_difficulty(
        ctx,
        level_id=level_id,
        demon_difficulty=demon_difficulty.as_difficulty(),
    )

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to set demon difficulty.",
            extra={
                "user_id": user.id,
                "level_id": level_id,
                "demon_difficulty": demon_difficulty,
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info(
        "Successfully set demon difficulty.",
        extra={
            "user_id": user.id,
            "level_id": level_id,
            "demon_difficulty": demon_difficulty,
        },
    )

    return responses.success()


async def custom_content_cdn_get(
    ctx: HTTPContext = Depends(),
):
    result = await songs.get_custom_content_url(ctx)

    if isinstance(result, ServiceError):
        logger.info(
            "Failed to serve custom content CDN url.",
            extra={
                "error": result.value,
            },
        )
        return responses.fail()

    logger.info("Successfully served custom content CDN url.")

    return result
