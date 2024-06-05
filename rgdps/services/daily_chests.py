from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import NamedTuple

from rgdps import repositories
from rgdps.common import gd_logic
from rgdps.common.context import Context
from rgdps.constants.daily_chests import DailyChestRewardType
from rgdps.constants.daily_chests import DailyChestType
from rgdps.constants.daily_chests import DailyChestView
from rgdps.constants.errors import ServiceError
from rgdps.models.daily_chest import DailyChest


class DailyChestInformation(NamedTuple):
    small_chest_time_remaining: timedelta
    large_chest_time_remaining: timedelta

    small_chest_count: int
    large_chest_count: int

    chest: DailyChest | None


SMALL_CHEST_TIME = timedelta(hours=2)
LARGE_CHEST_TIME = timedelta(hours=24)


# NOTE: This handles both just viewing and claiming a chest as GD handles
# both in a single endpoint.
async def view(
    ctx: Context,
    user_id: int,
    view: DailyChestView,
) -> DailyChestInformation | ServiceError:
    last_small_chest = await repositories.daily_chest.from_user_id_and_type_latest(
        ctx,
        user_id,
        DailyChestType.SMALL,
    )
    last_large_chest = await repositories.daily_chest.from_user_id_and_type_latest(
        ctx,
        user_id,
        DailyChestType.LARGE,
    )

    small_chest_count = await repositories.daily_chest.count_of_type(
        ctx,
        user_id,
        DailyChestType.SMALL,
    )
    large_chest_count = await repositories.daily_chest.count_of_type(
        ctx,
        user_id,
        DailyChestType.LARGE,
    )

    # Calculate the delays.
    current_ts = datetime.now()
    if last_small_chest:
        small_chest_time_remaining = SMALL_CHEST_TIME - (
            current_ts - last_small_chest.claimed_ts
        )
        if small_chest_time_remaining < timedelta():
            small_chest_time_remaining = timedelta()
    else:
        small_chest_time_remaining = timedelta()

    if last_large_chest:
        large_chest_time_remaining = LARGE_CHEST_TIME - (
            current_ts - last_large_chest.claimed_ts
        )
        if large_chest_time_remaining < timedelta():
            large_chest_time_remaining = timedelta()
    else:
        large_chest_time_remaining = timedelta()

    if not view.is_claim:
        return DailyChestInformation(
            small_chest_time_remaining,
            large_chest_time_remaining,
            small_chest_count,
            large_chest_count,
            None,
        )

    # Rewards
    mana = 0
    diamonds = 0
    fire_shards = 0
    ice_shards = 0
    poison_shards = 0
    shadow_shards = 0
    lava_shards = 0
    demon_keys = 0

    if view is DailyChestView.CLAIM_LARGE:
        if large_chest_time_remaining > timedelta():
            return ServiceError.DAILY_CHESTS_ALREADY_CLAIMED

        loot_table = gd_logic.get_large_chest
        chest_type = DailyChestType.LARGE
        large_chest_count += 1
        large_chest_time_remaining = LARGE_CHEST_TIME

    else:
        if small_chest_time_remaining > timedelta():
            return ServiceError.DAILY_CHESTS_ALREADY_CLAIMED

        loot_table = gd_logic.get_small_chest
        chest_type = DailyChestType.SMALL
        small_chest_count += 1
        small_chest_time_remaining = SMALL_CHEST_TIME

    rewards = loot_table()

    for reward in rewards:
        match reward.type:
            case DailyChestRewardType.MANA:
                mana += reward.amount
            case DailyChestRewardType.DIAMONDS:
                diamonds += reward.amount
            case DailyChestRewardType.FIRE_SHARD:
                fire_shards += reward.amount
            case DailyChestRewardType.ICE_SHARD:
                ice_shards += reward.amount
            case DailyChestRewardType.POISON_SHARD:
                poison_shards += reward.amount
            case DailyChestRewardType.SHADOW_SHARD:
                shadow_shards += reward.amount
            case DailyChestRewardType.LAVA_SHARD:
                lava_shards += reward.amount
            case DailyChestRewardType.DEMON_KEY:
                demon_keys += reward.amount

    # Award a key for every 500 mana the player gets.
    total_mana = await repositories.daily_chest.sum_reward_mana(ctx, user_id)
    total_keys = total_mana // 500

    new_total_keys = (total_mana + mana) // 500

    if new_total_keys > total_keys:
        demon_keys += new_total_keys - total_keys

    # Chest logging
    chest = await repositories.daily_chest.create(
        ctx,
        user_id=user_id,
        chest_type=chest_type,
        mana=mana,
        diamonds=diamonds,
        fire_shards=fire_shards,
        ice_shards=ice_shards,
        poison_shards=poison_shards,
        shadow_shards=shadow_shards,
        lava_shards=lava_shards,
        demon_keys=demon_keys,
    )

    return DailyChestInformation(
        small_chest_time_remaining,
        large_chest_time_remaining,
        small_chest_count,
        large_chest_count,
        chest,
    )
