from __future__ import annotations

from rgdps.adapters import AbstractStorage

class LevelData:
    """A wrapper class around pure-string level data for type
    clarity."""

    __slots__ = ("_data",)

    def __init__(self, data: str) -> None:
        self._data = data

    
    def data(self) -> str:
        return self._data
    

class LevelDataRepository:
    def __init__(self, storage: AbstractStorage) -> None:
        self._storage = storage

    
    async def from_user_id(self, user_id: str) -> LevelData | None:
        res = await self._storage.load(f"levels/{user_id}")
        if res is not None:
            return LevelData(res.decode())

        return None
    

    async def create(
            self,
            user_id: int,
            data: str,
    ) -> LevelData:
        await self._storage.save(f"levels/{user_id}", data.encode())
        return LevelData(data)
