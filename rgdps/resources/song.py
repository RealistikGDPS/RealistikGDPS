from __future__ import annotations

from enum import IntEnum

from rgdps.adapters import AbstractMySQLService
from rgdps.adapters import GeometryDashClient
from rgdps.adapters.boomlings import GDRequestStatus
from rgdps.common import modelling
from rgdps.resources._common import DatabaseModel

class SongSource(IntEnum):
    BOOMLINGS = 0
    NEWGROUNDS = 1
    CUSTOM = 2

class Song(DatabaseModel):
    id: int
    name: str
    author_id: int
    author: str
    author_youtube: str | None
    size: float
    download_url: str
    source: SongSource
    blocked: bool


ALL_FIELDS = modelling.get_model_fields(Song)
_ALL_FIELDS_COMMA = modelling.comma_separated(ALL_FIELDS)
_ALL_FIELDS_COLON = modelling.colon_prefixed_comma_separated(ALL_FIELDS)


class SongRepository:
    def __init__(
            self,
            mysql: AbstractMySQLService,
            geometry_dash: GeometryDashClient,
    ) -> None:
        self._mysql = mysql
        self._geometry_dash = geometry_dash

    
    async def __from_db(self, song_id: int, *, allow_blocked: bool = False) -> Song | None:
        song_db = await self._mysql.fetch_one(
            f"SELECT {_ALL_FIELDS_COMMA} FROM songs id = :song_id AND "
            "blocked IN :blocked",
            {
                "song_id": song_id,
                "blocked": (0, 1) if allow_blocked else (0,),
            },
        )

        if song_db is None:
            return None
    
        return Song(**song_db)
    

    async def __multiple_from_db(
            self,
            song_ids: list[int],
            *,
            allow_blocked: bool = False,
    ) -> list[Song]:
        songs_db = self._mysql.iterate(
            f"SELECT {_ALL_FIELDS_COMMA} FROM songs WHERE id IN :song_ids "
            "AND blocked IN :blocked",
            {
                "song_ids": tuple(song_ids),
                "blocked": (0, 1) if allow_blocked else (0,),
            },
        )

        return [Song(**song_db) async for song_db in songs_db]
    

    async def __from_boomlings(self, song_id: int) -> Song | None:
        song_boomlings = await self._geometry_dash.song_from_id(song_id)

        if isinstance(song_boomlings, GDRequestStatus):
            return None
        
        return Song(
            id=song_boomlings.id,
            name=song_boomlings.name,
            author_id=song_boomlings.author_id,
            author=song_boomlings.author,
            author_youtube=song_boomlings.author_youtube,
            size=song_boomlings.size,
            download_url=song_boomlings.download_url,
            source=SongSource.BOOMLINGS,
            blocked=False,
        )
    

    async def __insert_model(self, song_model: Song) -> int:
        return await self._mysql.execute(
            f"INSERT INTO songs ({_ALL_FIELDS_COMMA}) VALUES ({_ALL_FIELDS_COLON})",
            song_model.model_dump(),
        )
    

    async def create(
            self,
            name: str,
            author_id: int,
            author: str,
            download_url: str,
            author_youtube: str | None = None,
            size: float = 0.0,
            source: SongSource = SongSource.CUSTOM,
            blocked: bool = False,
            *,
            song_id: int | None = None,
    ) -> Song:
        song = Song(
            id=0,
            name=name,
            author_id=author_id,
            author=author,
            author_youtube=author_youtube,
            size=size,
            download_url=download_url,
            source=source,
            blocked=blocked,
        )
        song_dump = song.model_dump()
        song_dump["id"] = song_id

        return await self._mysql.execute(
            f"INSERT INTO songs ({_ALL_FIELDS_COMMA}) VALUES ({_ALL_FIELDS_COLON})",
            song_dump,
        )
    

    async def from_id(self, song_id: int, *, allow_blocked: bool = False) -> Song | None:
        song_db = await self.__from_db(song_id, allow_blocked=allow_blocked)

        if song_db is not None:
            return song_db
        
        song_gd = await self.__from_boomlings(song_id)

        if song_gd is not None:
            await self.__insert_model(song_gd)
        return song_gd
    

    async def multiple_from_id(self, song_ids: list[int], *, allow_blocked: bool = False) -> list[Song]:
        songs_db = await self.__multiple_from_db(song_ids, allow_blocked=allow_blocked)

        # All found within the database.
        if len(song_ids) == len(songs_db):
            return songs_db
        fetched_ids = [song.id for song in songs_db]

        # Fetch remaining results.
        for song_id in filter(lambda x: x not in fetched_ids, song_ids):
            song_boomlings = await self.__from_boomlings(song_id)
            if song_boomlings is None:
                continue

            songs_db.append(song_boomlings)

        return sorted(songs_db, key=lambda x: song_ids.index(x.id))
    

    async def count_all(self) -> int:
        return await self._mysql.fetch_val("SELECT COUNT(*) FROM songs")
