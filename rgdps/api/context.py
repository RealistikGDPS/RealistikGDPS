# from __future__ import annotations # This causes a pydantic issue. Yikes.

from typing import override

from fastapi import FastAPI
from fastapi import Request
from meilisearch_python_sdk import AsyncClient as MeiliClient
from redis.asyncio import Redis
from types_aiobotocore_s3 import S3Client

from rgdps.common.cache.base import AbstractAsyncCache
from rgdps.common.context import Context
from rgdps.adapters.boomlings import GeometryDashClient
from rgdps.adapters.mysql import AbstractMySQLService
from rgdps.adapters.storage import AbstractStorage


class HTTPContext(Context):
    def __init__(self, request: Request) -> None:
        self.request = request

    @override
    @property
    def mysql(self) -> AbstractMySQLService:
        # NOTE: This is a per-request transaction.
        return self.request.state.mysql

    @override
    @property
    def redis(self) -> Redis:
        return self.request.app.state.redis

    @override
    @property
    def meili(self) -> MeiliClient:
        return self.request.app.state.meili

    @override
    @property
    def storage(self) -> AbstractStorage:
        return self.request.app.state.storage

    @override
    @property
    def password_cache(self) -> AbstractAsyncCache[str]:
        return self.request.app.state.password_cache

    @override
    @property
    def gd(self) -> GeometryDashClient:
        return self.request.app.state.gd


# FIXME: Proper context for pubsub handlers that does not rely on app.
class PubsubContext(Context):
    """A shared context for pubsub handlers."""

    def __init__(self, app: FastAPI) -> None:
        self.state = app.state

    @override
    @property
    def mysql(self) -> AbstractMySQLService:
        return self.state.mysql

    @override
    @property
    def redis(self) -> Redis:
        return self.state.redis

    @override
    @property
    def meili(self) -> MeiliClient:
        return self.state.meili

    @override
    @property
    def s3(self) -> S3Client | None:
        return self.state.s3
    
    @override
    @property
    def password_cache(self) -> AbstractAsyncCache[str]:
        return self.state.password_cache

    @override
    @property
    def storage(self) -> AbstractStorage:
        return self.state.storage

    @override
    @property
    def gd(self) -> GeometryDashClient:
        return self.state.gd
