from __future__ import annotations

from rgdps.config import config


async def main_get() -> str:
    return f"{config.srv_name} - Powered by RealistikGDPS"
