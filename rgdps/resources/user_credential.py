from __future__ import annotations

from enum import IntEnum

from rgdps.adapters import AbstractMySQLService
from rgdps.common import modelling
from rgdps.resources._common import DatabaseModel

class CredentialVersion(IntEnum):
    PLAIN_BCRYPT = 1
    GJP2_BCRYPT = 2  # 2.2 + GJP2

class UserCredential(DatabaseModel):
    id: int
    user_id: int
    version: CredentialVersion
    value: str

ALL_FIELDS = modelling.get_model_fields(UserCredential)
CUSTOMISABLE_FIELDS = modelling.remove_id_field(ALL_FIELDS)


_ALL_FIELDS_COMMA = modelling.comma_separated(ALL_FIELDS)
_CUSTOMISABLE_FIELDS_COMMA = modelling.comma_separated(CUSTOMISABLE_FIELDS)
_ALL_FIELDS_COLON = modelling.colon_prefixed_comma_separated(ALL_FIELDS)
_CUSTOMISABLE_FIELDS_COLON = modelling.colon_prefixed_comma_separated(
    CUSTOMISABLE_FIELDS,
)

class UserCredentialRepository:
    def __init__(self, mysql: AbstractMySQLService) -> None:
        self._mysql = mysql

    
    async def create(
            self,
            user_id: int,
            credential_version: CredentialVersion,
            value: str,
    ) -> UserCredential:
        credential = UserCredential(
            id=0,
            user_id=user_id,
            version=credential_version,
            value=value,
        )

        credential.id = await self._mysql.execute(
            f"INSERT INTO user_credentials ({_CUSTOMISABLE_FIELDS_COMMA}) "
            f"VALUES ({_CUSTOMISABLE_FIELDS_COLON})",
            credential.model_dump(exclude={"id"}),
        )
        return credential
    

    async def from_user_id(
            self,
            user_id: int,
    ) -> UserCredential | None:
        res = await self._mysql.fetch_one(
            f"SELECT {_ALL_FIELDS_COMMA} FROM user_credentials WHERE user_id = :user_id "
            "ORDER BY id DESC LIMIT 1",
            {"user_id": user_id},
        )

        if not res:
            return None
        
        return UserCredential(**res)
    

    async def delete_from_user_id(self, user_id: int) -> None:
        await self._mysql.execute(
            "DELETE FROM user_credentials WHERE user_id = :user_id",
            {"user_id": user_id},
        )

    
    async def delete_from_id(self, credential_id: int) -> None:
        await self._mysql.execute(
            "DELETE FROM user_credentials WHERE id = :credential_id",
            {"credential_id": credential_id},
        )
