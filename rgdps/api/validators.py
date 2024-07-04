from __future__ import annotations

import re
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from rgdps.common import hashes

TEXT_BOX_REGEX = re.compile(r"^[a-zA-Z0-9 ]+$")
SOCIAL_MEDIA_REGEX = re.compile(r"^[\w\-.' ]+$")
# Its basically base64 string + ; + another base64 string
GAME_SAVE_DATA_REGEX = re.compile(
    r"^(?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]"
    r"{2}={2})\;(?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$",
)


class Base64String(str):
    @classmethod
    def encode(cls, value: str) -> Base64String:
        return Base64String(hashes.encode_base64(value))

    @classmethod
    def decode(cls, value: str) -> Base64String:
        return Base64String(hashes.decode_base64(value))

    @classmethod
    def _validate(cls, value: str) -> Base64String:
        if not isinstance(value, str):
            raise TypeError(f"Value must be str, got {type(value)}")

        try:
            return Base64String.decode(value)
        except Exception as e:
            raise ValueError("Failed to decode base64 string") from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )


class TextBoxString(str):
    @classmethod
    def _validate(cls, value: str) -> TextBoxString:
        if not isinstance(value, str):
            raise TypeError(f"Value must be str, got {type(value)}")

        # Value needs to be: stripped and alphanumeric.
        value = value.strip()

        if not TEXT_BOX_REGEX.match(value):
            raise ValueError("Value contains illegal characters")

        return TextBoxString(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )


class SocialMediaString(str):
    @classmethod
    def _validate(cls, value: str) -> TextBoxString:
        if not isinstance(value, str):
            raise TypeError(f"Value must be str, got {type(value)}")

        # Value needs to be: stripped and alphanumeric + it can contain `_`, `-`, `.`, and `'`.
        value = value.strip()

        if not SOCIAL_MEDIA_REGEX.match(value):
            raise ValueError("Value contains illegal characters")

        return TextBoxString(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )


class MessageContentString(str):
    @classmethod
    def _validate(cls, value: str) -> MessageContentString:
        if not isinstance(value, str):
            raise TypeError(f"Value must be str, got {type(value)}")

        try:
            return MessageContentString(hashes.decrypt_message_content(value))
        except Exception as e:
            raise ValueError("Failed to decrypt message content string") from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )


class CommaSeparatedIntList(list[int]):
    @classmethod
    def _validate(cls, value: list[str]) -> CommaSeparatedIntList:
        if not isinstance(value, list):
            raise TypeError(f"Value must be list, got {type(value)}")

        str_value = value[0]
        if not isinstance(str_value, str):
            raise TypeError(f"Value must be string, got {type(value)}")

        try:
            return CommaSeparatedIntList([int(x) for x in str_value.split(",")])
        except Exception as e:
            raise ValueError(f"Failed to convert list value to {int}") from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.list_schema(
                # XXX: due to type casting, fastapi converts the
                # string to a list with this one string
                # ensure that it's the only string in list.
                core_schema.str_schema(),
                min_length=1,
                max_length=1,
            ),
        )


class GameSaveData(str):
    @classmethod
    def url_encode(cls, value: str) -> GameSaveData:
        return GameSaveData(value.replace("+", "-").replace("/", "_"))

    @classmethod
    def url_decode(cls, value: str) -> GameSaveData:
        return GameSaveData(value.replace("-", "+").replace("_", "/"))

    @classmethod
    def _validate(cls, value: str) -> GameSaveData:
        if not isinstance(value, str):
            raise TypeError(f"Value must be str, got {type(value)}")

        url_decoded = GameSaveData.url_decode(value)
        if not GAME_SAVE_DATA_REGEX.match(url_decoded):
            raise ValueError("Invalid save data format")

        # save data usually send the game manager data and local maps
        if not value.count("H4sIAAAAAAAA") == 2:
            raise ValueError("Invalid save data format")

        if value.find(";H4sIAAAAAAAA") == -1:
            raise ValueError("Invalid save data format")

        return GameSaveData(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _: Any,
        __: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
