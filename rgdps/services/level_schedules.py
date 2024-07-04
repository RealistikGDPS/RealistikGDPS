from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import NamedTuple

from rgdps import repositories
from rgdps.common.context import Context
from rgdps.common.data_utils import linear_biased_random
from rgdps.constants.errors import ServiceError
from rgdps.constants.level_schedules import LevelScheduleType
from rgdps.constants.levels import LevelLength
from rgdps.models.level import Level
from rgdps.models.level_schedule import LevelSchedule


async def schedule_next(
    ctx: Context,
    schedule_type: LevelScheduleType,
    level_id: int,
    scheduled_by_id: int | None = None,
) -> LevelSchedule | ServiceError:
    # Ensure the level works.
    level = await repositories.level.from_id(ctx, level_id)
    if level is None:
        return ServiceError.LEVELS_NOT_FOUND

    # Enqueue it after the next level of this type.
    prev_schedule = await repositories.level_schedule.get_last(
        ctx,
        schedule_type,
    )

    if prev_schedule is None:
        start_time = datetime.now()
    else:
        start_time = prev_schedule.end_time

    if schedule_type == LevelScheduleType.WEEKLY:
        end_time = start_time + timedelta(days=7)
    else:
        end_time = start_time + timedelta(days=1)

    schedule = await repositories.level_schedule.create(
        ctx,
        schedule_type,
        level_id,
        start_time,
        end_time,
        scheduled_by_id,
    )

    return schedule


# XXX: This may benefit from locking.
# For daily levels, we will have an algorithm that automatically nominates a level
# iff there is no level that has been scheduled for today.
# Conditions for a level to be automatically nominated:
# - Rated over 1 star
# - Rated below 8 stars
# - High like to download ratio, with an emphasis on lower downloads.
# - At least medium length
# - Hasn't been daily in the last 20 days.

DAILY_LEVELS_TO_EXCLUDE = (
    20  # TODO: look into scaling this with the number of levels on the server.
)


# Helper function to separate the algorithm.
async def _auto_nominate_daily(ctx: Context) -> LevelSchedule | None:
    last_n = await repositories.level_schedule.get_last_n(
        ctx,
        LevelScheduleType.DAILY,
        DAILY_LEVELS_TO_EXCLUDE,
    )

    excluded_level_ids = [schedule.level_id for schedule in last_n]

    recommendations = await repositories.level.get_well_received(
        ctx,
        minimum_stars=2,
        maximum_stars=7,
        minimum_length=LevelLength.MEDIUM,
        excluded_level_ids=excluded_level_ids,
        limit=20,
    )

    if not recommendations:
        return None

    # Choose a random level with a bias towards lower indexes.
    level_id = linear_biased_random(recommendations)

    level = await repositories.level.from_id(
        ctx,
        level_id,
    )

    # Give up (rare branch), will likely be re-attempted soon.
    if level is None:
        return None

    return await repositories.level_schedule.create(
        ctx,
        LevelScheduleType.DAILY,
        level_id,
    )


# For weekly levels, we have a less strict algorithm.
# Conditions for a level to be automatically nominated:
# - Easy to Hard demon.
# - High like to download ratio, with an emphasis on lower downloads.
# - At least medium length
# - Hasn't been daily in the last 52 days.

WEEKLY_LEVELS_TO_EXCLUDE = 52 // 7


# For now, this is rather similar to the daily algorithm, but may change in the future.
async def _auto_nominate_weekly(ctx: Context) -> LevelSchedule | None:
    last_n = await repositories.level_schedule.get_last_n(
        ctx,
        LevelScheduleType.DAILY,
        WEEKLY_LEVELS_TO_EXCLUDE,
    )

    excluded_level_ids = [schedule.level_id for schedule in last_n]

    recommendations = await repositories.level.get_well_received(
        ctx,
        minimum_stars=10,
        maximum_stars=10,
        minimum_length=LevelLength.MEDIUM,
        excluded_level_ids=excluded_level_ids,
        limit=20,
    )

    if not recommendations:
        return None

    # Choose a random level with a bias towards lower indexes.
    level_id = linear_biased_random(recommendations)

    level = await repositories.level.from_id(
        ctx,
        level_id,
    )

    # Give up (rare branch), will likely be re-attempted soon.
    if level is None:
        return None

    return await repositories.level_schedule.create(
        ctx,
        LevelScheduleType.WEEKLY,
        level_id,
    )


class ScheduledLevel(NamedTuple):
    schedule: LevelSchedule
    level: Level


async def get_current(
    ctx: Context,
    schedule_type: LevelScheduleType,
) -> ScheduledLevel | ServiceError:
    schedule = await repositories.level_schedule.get_current(
        ctx,
        schedule_type,
    )

    if schedule is None:
        if schedule_type == LevelScheduleType.DAILY:
            schedule = await _auto_nominate_daily(ctx)
        elif schedule_type == LevelScheduleType.WEEKLY:
            schedule = await _auto_nominate_weekly(ctx)

    if schedule is None:
        return ServiceError.LEVEL_SCHEDULE_UNSET

    level = await repositories.level.from_id(
        ctx,
        schedule.level_id,
    )

    if level is None:
        return ServiceError.LEVELS_NOT_FOUND

    return ScheduledLevel(
        schedule=schedule,
        level=level,
    )
