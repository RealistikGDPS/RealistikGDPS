from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

from meilisearch_python_sdk import AsyncClient as MeiliClient
from redis.asyncio import Redis

if TYPE_CHECKING:
    from rgdps.common.cache.base import AbstractAsyncCache
    from rgdps.models.user import User
    from rgdps.adapters.boomlings import GeometryDashClient
    from rgdps.adapters.mysql import AbstractMySQLService
    from rgdps.adapters.storage import AbstractStorage


class Context(ABC):
    @property
    @abstractmethod
    def mysql(self) -> AbstractMySQLService: ...

    @property
    @abstractmethod
    def redis(self) -> Redis: ...

    @property
    @abstractmethod
    def meili(self) -> MeiliClient: ...

    @property
    @abstractmethod
    def storage(self) -> AbstractStorage: ...

    @property
    @abstractmethod
    def password_cache(self) -> AbstractAsyncCache[str]: ...

    @property
    @abstractmethod
    def gd(self) -> GeometryDashClient: ...
