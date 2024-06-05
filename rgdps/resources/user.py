from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from enum import IntFlag
from typing import Any
from typing import AsyncGenerator
from typing import TypedDict
from typing import NotRequired
from typing import Unpack

from rgdps.common.mixins import IntEnumStringMixin
from rgdps.adapters import AbstractMySQLService
from rgdps.adapters import MeiliSearchClient
from rgdps.common import modelling
from rgdps.common.colour import Colour
from rgdps.common import time as time_utils
from rgdps.resources._common import DatabaseModel
from rgdps.resources._common import SearchResults


# TODO: Move all of these to string enums and then have a GD equivalent.
class UserPrivileges(IntFlag):
    USER_AUTHENTICATE = 1 << 0
    USER_PROFILE_PUBLIC = 1 << 1
    USER_STAR_LEADERBOARD_PUBLIC = 1 << 2
    USER_CREATOR_LEADERBOARD_PUBLIC = 1 << 3
    USER_DISPLAY_ELDER_BADGE = 1 << 4
    USER_DISPLAY_MOD_BADGE = 1 << 5
    USER_REQUEST_ELDER = 1 << 6
    USER_REQUEST_MODERATOR = 1 << 7
    USER_CREATE_USER_COMMENTS = 1 << 8
    USER_MODIFY_PRIVILEGES = 1 << 9
    USER_CHANGE_CREDENTIALS_OWN = 1 << 10
    USER_CHANGE_CREDENTIALS_OTHER = 1 << 11

    LEVEL_UPLOAD = 1 << 12
    LEVEL_UPDATE = 1 << 13
    LEVEL_DELETE_OWN = 1 << 14
    LEVEL_DELETE_OTHER = 1 << 15
    LEVEL_RATE_STARS = 1 << 16
    LEVEL_ENQUEUE_DAILY = 1 << 17
    LEVEL_ENQUEUE_WEEKLY = 1 << 18
    LEVEL_MODIFY_VISIBILITY = 1 << 19
    LEVEL_RENAME_OTHER = 1 << 20
    LEVEL_MARK_MAGIC = 1 << 21
    LEVEL_MARK_AWARDED = 1 << 22

    COMMENTS_POST = 1 << 23
    COMMENTS_DELETE_OWN = 1 << 24
    COMMENTS_DELETE_OTHER = 1 << 25
    COMMANDS_TRIGGER = 1 << 26
    COMMENTS_BYPASS_SPAM_FILTER = 1 << 27

    MESSAGES_SEND = 1 << 28
    MESSAGES_DELETE_OWN = 1 << 29

    FRIEND_REQUESTS_SEND = 1 << 30
    FRIEND_REQUESTS_ACCEPT = 1 << 31
    FRIEND_REQUESTS_DELETE_OWN = 1 << 32

    MAP_PACK_CREATE = 1 << 33

    GAUNTLET_CREATE = 1 << 34

    SERVER_RESYNC_SEARCH = 1 << 35
    SERVER_STOP = 1 << 36

    USER_VIEW_PRIVATE_PROFILE = 1 << 37
    COMMENTS_LIKE = 1 << 38

    LEVEL_CHANGE_DESCRIPTION_OTHER = 1 << 39

    SERVER_RESYNC_LEADERBOARDS = 1 << 40

    LEVEL_MOVE_USER = 1 << 41

    def as_bytes(self) -> bytes:
        return self.to_bytes(16, "little", signed=False)

    @staticmethod
    def from_db_bytes(b: bytes) -> UserPrivileges:
        return UserPrivileges(int.from_bytes(b, "little", signed=False))


class UserPrivacySetting(IntEnum):
    PUBLIC = 0
    FRIENDS = 1
    PRIVATE = 2


class UserPrivilegeLevel(IntEnumStringMixin, IntEnum):
    """Enum for determining whether a user should be displayed as a
    moderator, elder moderator, or neither.
    """

    NONE = 0
    MODERATOR = 1
    ELDER_MODERATOR = 2


# TODO: Move
STAR_PRIVILEGES = (
    UserPrivileges.USER_STAR_LEADERBOARD_PUBLIC | UserPrivileges.USER_PROFILE_PUBLIC
)
"""A set of privileges required for a user to appear on the star leaderboards."""

CREATOR_PRIVILEGES = (
    UserPrivileges.USER_CREATOR_LEADERBOARD_PUBLIC | UserPrivileges.USER_PROFILE_PUBLIC
)
"""A set of privileges required for a user to appear on the creator leaderboards."""

DEFAULT_PRIVILEGES = (
    UserPrivileges.USER_AUTHENTICATE
    | UserPrivileges.USER_PROFILE_PUBLIC
    | UserPrivileges.USER_STAR_LEADERBOARD_PUBLIC
    | UserPrivileges.USER_CREATOR_LEADERBOARD_PUBLIC
    | UserPrivileges.USER_CREATE_USER_COMMENTS
    | UserPrivileges.USER_CHANGE_CREDENTIALS_OWN
    | UserPrivileges.LEVEL_UPLOAD
    | UserPrivileges.LEVEL_UPDATE
    | UserPrivileges.LEVEL_DELETE_OWN
    | UserPrivileges.COMMENTS_POST
    | UserPrivileges.COMMENTS_DELETE_OWN
    | UserPrivileges.COMMANDS_TRIGGER
    | UserPrivileges.MESSAGES_SEND
    | UserPrivileges.MESSAGES_DELETE_OWN
    | UserPrivileges.FRIEND_REQUESTS_SEND
    | UserPrivileges.FRIEND_REQUESTS_ACCEPT
    | UserPrivileges.FRIEND_REQUESTS_DELETE_OWN
    | UserPrivileges.COMMENTS_LIKE
)
"""A set of default privileges to be assigned to users upon registration."""

class User(DatabaseModel):
    id: int
    username: str
    email: str
    privileges: UserPrivileges

    message_privacy: UserPrivacySetting
    friend_privacy: UserPrivacySetting
    comment_privacy: UserPrivacySetting

    youtube_name: str | None
    twitter_name: str | None
    twitch_name: str | None

    register_ts: datetime
    comment_colour: Colour

    # TODO: Move?
    stars: int
    demons: int
    moons: int
    primary_colour: int
    secondary_colour: int
    glow_colour: int
    display_type: int
    icon: int
    ship: int
    ball: int
    ufo: int
    wave: int
    robot: int
    spider: int
    swing_copter: int
    jetpack: int
    explosion: int
    glow: bool
    creator_points: int
    coins: int
    user_coins: int
    diamonds: int


# In case we want to move to a less direct model approach later.
type UserModel = User

ALL_FIELDS = modelling.get_model_fields(User)
CUSTOMISABLE_FIELDS = modelling.remove_id_field(ALL_FIELDS)


_ALL_FIELDS_COMMA = modelling.comma_separated(ALL_FIELDS)
_ALL_FIELDS_COLON = modelling.colon_prefixed_comma_separated(ALL_FIELDS)

DEFAULT_PAGE_SIZE = 10

class _UserUpdatePartial(TypedDict):
    """Set of optional key-word arguments that may be used to update a user."""

    username: NotRequired[str]
    email: NotRequired[str]
    privileges: NotRequired[UserPrivileges]
    message_privacy: NotRequired[UserPrivacySetting]
    friend_privacy: NotRequired[UserPrivacySetting]
    comment_privacy: NotRequired[UserPrivacySetting]
    youtube_name: NotRequired[str | None]
    twitter_name: NotRequired[str | None]
    twitch_name: NotRequired[str | None]
    stars: NotRequired[int]
    demons: NotRequired[int]
    moons: NotRequired[int]
    primary_colour: NotRequired[int]
    secondary_colour: NotRequired[int]
    glow_colour: NotRequired[int]
    display_type: NotRequired[int]
    icon: NotRequired[int]
    ship: NotRequired[int]
    ball: NotRequired[int]
    ufo: NotRequired[int]
    wave: NotRequired[int]
    robot: NotRequired[int]
    spider: NotRequired[int]
    swing_copter: NotRequired[int]
    jetpack: NotRequired[int]
    explosion: NotRequired[int]
    glow: NotRequired[bool]
    creator_points: NotRequired[int]
    coins: NotRequired[int]
    user_coins: NotRequired[int]
    diamonds: NotRequired[int]
    comment_colour: NotRequired[Colour]

# Meili type accommodation.
def _meili_dict_from_model(user_model: UserModel) -> dict[str, Any]:
    return _meili_dict_from_dict(user_model.model_dump())

def _meili_dict_from_dict(user_dict: dict[str, Any]) -> dict[str, Any]:
    if "privileges" in user_dict:
        user_dict["privileges"] = int.from_bytes(
            user_dict["privileges"],
            byteorder="little",
            signed=False,
        )
        user_dict["is_public"] = (
            user_dict["privileges"] & UserPrivileges.USER_PROFILE_PUBLIC > 0
        )

    if "register_ts" in user_dict:
        user_dict["register_ts"] = time_utils.into_unix_ts(user_dict["register_ts"])

    return user_dict


def _model_from_meili_dict(user_dict: dict[str, Any]) -> UserModel:
    user_dict = user_dict.copy()

    user_dict["privileges"] = UserPrivileges(int(user_dict["privileges"])).as_bytes()

    user_dict["register_ts"] = time_utils.from_unix_ts(user_dict["register_ts"])

    del user_dict["is_public"]

    return User(**user_dict)


class UserRepository:
    def __init__(
            self,
            mysql: AbstractMySQLService,
            meili: MeiliSearchClient,
    ) -> None:
        self._mysql = mysql
        self._meili = meili.index("users")

    
    async def from_id(self, user_id: int) -> User | None:
        user_db = await self._mysql.fetch_one(
            f"SELECT {_ALL_FIELDS_COMMA} FROM users WHERE id = :id",
            {"id": user_id},
        )

        if user_db is None:
            return None
        
        return User(**user_db)
    

    async def multiple_from_id(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        
        users_db = self._mysql.iterate(
            f"SELECT {_ALL_FIELDS_COMMA} FROM users WHERE id IN :ids",
            {"ids": tuple(user_ids)},
        )

        return [User(**user_row) async for user_row in users_db]
    

    async def __update_meili(self, model: User) -> None:
        user_dict = _meili_dict_from_model(model)
        await self._meili.add_documents([user_dict])


    async def create(
            self,
            username: str,
            email: str,
            *,
            privileges: UserPrivileges = DEFAULT_PRIVILEGES,
            message_privacy: UserPrivacySetting = UserPrivacySetting.PUBLIC,
            friend_privacy: UserPrivacySetting = UserPrivacySetting.PUBLIC,
            comment_privacy: UserPrivacySetting = UserPrivacySetting.PUBLIC,
            youtube_name: str | None = None,
            twitter_name: str | None = None,
            twitch_name: str | None = None,
            register_ts: datetime | None = None,
            stars: int = 0,
            demons: int = 0,
            moons: int = 0,
            primary_colour: int = 0,
            # NOTE: secondary_colour is 4 by default in the game
            secondary_colour: int = 4,
            glow_colour: int = 0,
            display_type: int = 0,
            icon: int = 0,
            ship: int = 0,
            ball: int = 0,
            ufo: int = 0,
            wave: int = 0,
            robot: int = 0,
            spider: int = 0,
            swing_copter: int = 0,
            jetpack: int = 0,
            explosion: int = 0,
            glow: bool = False,
            creator_points: int = 0,
            coins: int = 0,
            user_coins: int = 0,
            diamonds: int = 0,
            user_id: int | None = 0,
            comment_colour: Colour = Colour.default(),
    ) -> User:
        if register_ts is None:
            register_ts = datetime.now()

        user_id_provided = user_id is not None
        if user_id is None:
            user_id = 0

        user = User(
            id=user_id,
            username=username,
            email=email,
            privileges=privileges,
            message_privacy=message_privacy,
            friend_privacy=friend_privacy,
            comment_privacy=comment_privacy,
            youtube_name=youtube_name,
            twitter_name=twitter_name,
            twitch_name=twitch_name,
            register_ts=register_ts,
            stars=stars,
            demons=demons,
            moons=moons,
            primary_colour=primary_colour,
            secondary_colour=secondary_colour,
            glow_colour=glow_colour,
            display_type=display_type,
            icon=icon,
            ship=ship,
            ball=ball,
            ufo=ufo,
            wave=wave,
            robot=robot,
            spider=spider,
            swing_copter=swing_copter,
            jetpack=jetpack,
            explosion=explosion,
            glow=glow,
            creator_points=creator_points,
            coins=coins,
            user_coins=user_coins,
            diamonds=diamonds,
            comment_colour=comment_colour
        )

        if user_id_provided:
            user_dict = user.model_dump()
        else:
            user_dict = user.model_dump(exclude={"id"}) | {
                "id": None,
            }

        user.id = await self._mysql.execute(
            f"INSERT INTO users ({_ALL_FIELDS_COMMA}) VALUES ({_ALL_FIELDS_COLON})",
            user_dict,
        )

        await self.__update_meili(user)
        return user
    

    async def update_partial(
            self,
            user_id: int,
            **kwargs: Unpack[_UserUpdatePartial],
    ) -> User | None:
        changed_fields = modelling.unpack_enum_types(kwargs)

        await self._mysql.execute(
            modelling.update_from_partial_dict("users", user_id, changed_fields),
            changed_fields,
        )

        meili_dict = _meili_dict_from_dict(dict(kwargs)) | {
            "id": user_id,
        }

        await self._meili.update_documents([meili_dict])
        return await self.from_id(user_id)
    

    async def from_username(self, username: str) -> User | None:
        user_id = await self._mysql.fetch_val(
            "SELECT id FROM users WHERE username = :username",
            {"username": username},
        )

        if user_id is None:
            return None
        
        return await self.from_id(user_id)
    

    async def all(self) -> AsyncGenerator[User, None]:
        async for user_db in self._mysql.iterate(
            f"SELECT {_ALL_FIELDS_COMMA} FROM users"
        ):
            yield User(**user_db)
    

    # Search related.
    async def search(
            self,
            query: str,
            *,
            page: int = 0,
            page_size: int = DEFAULT_PAGE_SIZE,
            include_hidden: bool = False,
    ) -> SearchResults[User]:
        filters = []
        if not include_hidden:
            filters.append("is_public = true")

        results_db = await self._meili.search(
            query,
            offset=page * page_size,
            limit=page_size,
            filter=filters,
        )

        results = [
            _model_from_meili_dict(result) for result in results_db.hits
        ]

        return SearchResults(
            results,
            results_db.estimated_total_hits or 0,
            page_size,
        )
    

    # Non-model related checks.
    async def is_email_available(self, email: str) -> bool:
        return not self._mysql.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM users WHERE email = :email)",
            {
                "email": email,
            },
        )
    

    async def is_username_available(self, username: str) -> bool:
        return not self._mysql.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM users WHERE username = :username)",
            {
                "username": username,
            },
        )
    

    async def count_all(self) -> int:
        return await self._mysql.fetch_val("SELECT COUNT(*) FROM users")
