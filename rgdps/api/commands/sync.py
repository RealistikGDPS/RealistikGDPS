from __future__ import annotations

import asyncio

from rgdps.api.commands.framework import CommandContext
from rgdps.api.commands.framework import CommandRouter
from rgdps.constants.users import UserPrivileges
from rgdps.services import leaderboards
from rgdps.services import levels
from rgdps.services import users

router = CommandRouter("sunc_root")

# Main level command group.
sync_group = CommandRouter("sync")
router.register_command(sync_group)


@sync_group.register_function(
    name="levels",
    required_privileges=UserPrivileges.SERVER_RESYNC_SEARCH,
)
async def level_search(ctx: CommandContext) -> str:
    asyncio.create_task(levels.synchronise_search(ctx))

    return "Search synchronisation scheduled."


@sync_group.register_function(
    name="leaderboards",
    required_privileges=UserPrivileges.SERVER_RESYNC_LEADERBOARDS,
)
async def leaderboard_search(ctx: CommandContext) -> str:
    asyncio.create_task(leaderboards.synchronise_top_stars(ctx))
    asyncio.create_task(leaderboards.synchronise_top_creators(ctx))

    return "Leaderboard synchronisation scheduled."


@sync_group.register_function(
    name="users",
    required_privileges=UserPrivileges.SERVER_RESYNC_SEARCH,
)
async def user_search(ctx: CommandContext) -> str:
    asyncio.create_task(users.synchronise_search(ctx))

    return "User search synchronisation scheduled."
