#!/usr/bin/env python3.12
from __future__ import annotations

from rgdps import settings
import ddtrace

if settings.DD_ENABLED:
    ddtrace.tracer.configure(
        https=False,
        hostname=settings.DD_HOST,
        port=settings.DD_PORT,
        dogstatsd_url=f"udp://{settings.DD_STATS_HOST}:{settings.DD_STATS_PORT}",
    )

    # TODO: bump ddtrace when fastapi and starlette patches work again
    ddtrace.patch_all(fastapi=False, starlette=False)

import sys

from rgdps.api import init_api

if sys.platform != "win32":
    import uvloop

    uvloop.install()
else:
    import winloop

    winloop.install()

asgi_app = init_api()
