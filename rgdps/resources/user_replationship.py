from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import NotRequired
from typing import TypedDict
from typing import Unpack

from rgdps.adapters import AbstractMySQLService
from rgdps.common import modelling
from rgdps.resources._common import DatabaseModel

class UserRelationshipType(IntEnum):
    FRIEND = 0
    BLOCKED = 1

class UserRelationship(DatabaseModel):
    id: int
    relationship_type: UserRelationshipType
    user_id: int
    target_user_id: int
    post_ts: datetime
    seen_ts: datetime | None

DEFAULT_PAGE_SIZE = 10

ALL_FIELDS = modelling.get_model_fields(UserRelationship)
CUSTOMISABLE_FIELDS = modelling.remove_id_field(ALL_FIELDS)


_ALL_FIELDS_COMMA = modelling.comma_separated(ALL_FIELDS)
_CUSTOMISABLE_FIELDS_COMMA = modelling.comma_separated(CUSTOMISABLE_FIELDS)
_CUSTOMISABLE_FIELDS_COLON = modelling.colon_prefixed_comma_separated(
    CUSTOMISABLE_FIELDS,
)

class _UserRelationshipUpdatePartial(TypedDict):
    seen_ts: NotRequired[datetime]
    deleted: NotRequired[bool]

class UserRelationshipRepository:
    def __init__(self, mysql: AbstractMySQLService) -> None:
        self._mysql = mysql

    
    async def from_id(
            self,
            relationship_id: int,
            *,
            include_deleted: bool = False,
    ) -> UserRelationship | None:
        condition = "AND NOT deleted" if not include_deleted else ""

        relationship_db = await self._mysql.fetch_one(
            f"SELECT {_ALL_FIELDS_COMMA} FROM user_relationships WHERE id = "
            f":relationship_id {condition}",
            {"relationship_id": relationship_id},
        )

        if not relationship_db:
            return None
        
        return UserRelationship(**relationship_db)
    

    async def create(
            self,
            user_id: int,
            target_user_id: int,
            relationship_type: UserRelationshipType,
            post_ts: datetime | None = None,
            seen_ts: datetime | None = None,
    ) -> UserRelationship:
        if post_ts is None:
            post_ts = datetime.now()

        relationship = UserRelationship(
            id=0,
            relationship_type=relationship_type,
            user_id=user_id,
            target_user_id=target_user_id,
            post_ts=post_ts,
            seen_ts=seen_ts,
        )

        relationship.id = await self._mysql.execute(
            f"INSERT INTO user_relationships ({_CUSTOMISABLE_FIELDS_COMMA}) "
            f"VALUES ({_CUSTOMISABLE_FIELDS_COLON})",
            relationship.model_dump(exclude={"id"}),
        )
        return relationship
    

    # TODO: The API here might be made nicer.
    async def from_user_id(
            self,
            user_id: int,
            relationship_type: UserRelationshipType,
            *,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        condition = "AND NOT deleted" if not include_deleted else ""

        relationships_db = self._mysql.iterate(
            f"SELECT {_ALL_FIELDS_COMMA} FROM user_relationships WHERE user_id = :user_id AND "
            f"relationship_type = :relationship_type {condition} "
            "ORDER BY post_ts DESC",
            {"user_id": user_id, "relationship_type": relationship_type.value},
        )

        return [
            UserRelationship(**relationship_row)
            async for relationship_row in relationships_db
        ]
    

    async def from_user_id_paginated(
            self,
            user_id: int,
            relationship_type: UserRelationshipType,
            *,
            page: int = 0,
            page_size: int = DEFAULT_PAGE_SIZE,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        condition = "AND NOT deleted" if not include_deleted else ""

        relationships_db = self._mysql.iterate(
            f"SELECT {_ALL_FIELDS_COMMA} FROM user_relationships WHERE user_id = :user_id AND "
            f"relationship_type = :relationship_type {condition} "
            "ORDER BY post_ts DESC LIMIT :limit OFFSET :offset",
            {
                "user_id": user_id,
                "relationship_type": relationship_type.value,
                "limit": page_size,
                "offset": page * page_size,
            },
        )

        return [
            UserRelationship(**relationship_row)
            async for relationship_row in relationships_db
        ]
    
    # The nicer API in question.
    async def blocked_from_user_id(
            self,
            user_id: int,
            *,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        return await self.from_user_id(
            user_id,
            UserRelationshipType.BLOCKED,
            include_deleted=include_deleted,
        )
    

    async def blocked_from_user_id_paginated(
            self,
            user_id: int,
            *,
            page: int = 0,
            page_size: int = DEFAULT_PAGE_SIZE,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        return await self.from_user_id_paginated(
            user_id,
            UserRelationshipType.BLOCKED,
            include_deleted=include_deleted,
            page=page,
            page_size=page_size,
        )
    

    async def friends_from_user_id(
            self,
            user_id: int,
            *,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        return await self.from_user_id(
            user_id,
            UserRelationshipType.FRIEND,
            include_deleted=include_deleted,
        )
    

    async def friends_from_user_id_paginated(
            self,
            user_id: int,
            *,
            page: int = 0,
            page_size: int = DEFAULT_PAGE_SIZE,
            include_deleted: bool = False,
    ) -> list[UserRelationship]:
        return await self.from_user_id_paginated(
            user_id,
            UserRelationshipType.FRIEND,
            include_deleted=include_deleted,
            page=page,
            page_size=page_size,
        )
    

    async def from_user_and_target(
            self,
            user_id: int,
            target_user_id: int,
            *,
            include_deleted: bool = False,
    ) -> UserRelationship | None:
        condition = "AND NOT deleted" if not include_deleted else ""

        result_db = await self._mysql.fetch_one(
            f"SELECT {_ALL_FIELDS_COMMA} FROM user_relationships WHERE "
            f"user_id = :user_id AND target_user_id = :target_user_id {condition} "
            "ORDER BY id DESC",
            {"user_id": user_id, "target_user_id": target_user_id}
        )

        if result_db is None:
            return None
        
        return UserRelationship(**result_db)
    

    async def count_user_relationships(
            self,
            user_id: int,
            relationship_type: UserRelationshipType,
            *,
            include_deleted: bool = False,
    ) -> int:
        condition = "AND NOT deleted" if not include_deleted else ""

        return await self._mysql.fetch_val(
            "SELECT COUNT(*) FROM user_relationships WHERE user_id = :user_id "
            f"AND relationship_type = :relationship_type {condition}",
            {"user_id": user_id, "relationship_type": relationship_type.value},
        )
    

    async def count_unseen_user_relationships(
            self,
            user_id: int,
            relationship_type: UserRelationshipType,
            *,
            include_deleted: bool = False,
    ) -> int:
        condition = "AND NOT deleted" if not include_deleted else ""

        return await self._mysql.fetch_val(
            "SELECT COUNT(*) FROM user_relationships WHERE user_id = :user_id "
            f"AND relationship_type = :relationship_type AND seen_ts = NULL {condition}",
            {"user_id": user_id, "relationship_type": relationship_type.value},
        )
    

    async def update_partial(
            self,
            relationship_id: int,
            **kwargs: Unpack[_UserRelationshipUpdatePartial],
    ) -> UserRelationship | None:
        changed_fields = modelling.unpack_enum_types(kwargs)

        await self._mysql.execute(
            modelling.update_from_partial_dict(
                "user_relationships",
                relationship_id,
                changed_fields,
            ),
            changed_fields,
        )

        return await self.from_id(relationship_id, include_deleted=True)
    

    async def count_all(self) -> int:
        return await self._mysql.fetch_val("SELECT COUNT(*) FROM user_relationships")
