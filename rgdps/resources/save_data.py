from __future__ import annotations

from rgdps.adapters import AbstractStorage

class SaveData:
    """A wrapper class around a pure-string save data for type
    clarity."""

    __slots__ = ("_data",)

    def __init__(self, data: str) -> None:
        self._data = data

    
    def data(self) -> str:
        return self._data
    

class SaveDataRepository:
    def __init__(self, storage: AbstractStorage) -> None:
        self._storage = storage

    
    async def from_user_id(self, user_id: str) -> SaveData | None:
        res = await self._storage.load(f"saves/{user_id}")
        if res is not None:
            return SaveData(res.decode())

        return None
    

    async def create(
            self,
            user_id: int,
            data: str,
    ) -> SaveData:
        await self._storage.save(f"saves/{user_id}", data.encode())
        return SaveData(data)
