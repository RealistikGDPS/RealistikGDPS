from __future__ import annotations

from rgdps import settings


async def main_get() -> str:
    return f"{settings.SERVER_NAME} - Powered by RealistikGDPS"
