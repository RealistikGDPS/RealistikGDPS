from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from .save_data import SaveData
from .save_data import SaveDataRepository

from .user import User
from .user import UserRepository

from .level_data import LevelData
from .level_data import LevelDataRepository

from .user_replationship import UserRelationship
from .user_replationship import UserRelationshipRepository
from .user_replationship import UserRelationshipType

from .user_credential import UserCredential
from .user_credential import UserCredentialRepository

class Context(ABC):
    @property
    @abstractmethod
    def save_data(self) -> SaveDataRepository: ...

    @property
    @abstractmethod
    def users(self) -> UserRepository: ...

    @property
    @abstractmethod
    def level_data(self) -> LevelDataRepository: ...

    @property
    @abstractmethod
    def relationships(self) -> UserRelationshipRepository: ...


    @property
    @abstractmethod
    def credentials(self) -> UserCredentialRepository: ...
