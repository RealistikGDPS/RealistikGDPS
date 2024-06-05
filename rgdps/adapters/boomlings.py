from __future__ import annotations

from enum import Enum
from typing import Any
from urllib.parse import unquote

import httpx
from pydantic import BaseModel

from rgdps import logger
from rgdps.common import gd_obj


class GDRequestStatus(str, Enum):
    """Returns the outcome status of a Geometry Dash request, including
    success."""

    NONE = "none"
    NOT_FOUND = "not_found"
    CLOUDFLARE_ERROR = "cloudflare_error"
    ROBTOP_BLACKLIST = "robtop_blacklist"
    SERVER_ERROR = "request_error"

    @property
    def is_error(self) -> bool:
        """Checks if the request encountered an issue."""

        return self != GDRequestStatus.NONE

    @property
    def is_severe_error(self) -> bool:
        """Checks if the request encountered an issue that should
        warrant an investivation."""

        return self in _SEVERE_ERRORS


_SEVERE_ERRORS = (
    GDRequestStatus.CLOUDFLARE_ERROR,
    GDRequestStatus.ROBTOP_BLACKLIST,
    GDRequestStatus.SERVER_ERROR,
)


GEOMETRY_DASH_URL = "https://www.boomlings.com/database"
"""The default URL to access Geometry Dash's servers."""

# This is meant to be an empty string.
GEOMETRY_DASH_HEADER = ""
"""The User-Agent header used by the client. This is specifically checked
for by the firewall."""

_CLOUDFLARE_ERROR_RESPONSE = "error code: 1005"
"""A Cloudflare firewall response if your response was blocked with an empty
User-Agent header."""

_ROBTOP_ERROR_RESPONSE = "no"
"""Unknown fully but generally if rob does something personally against you/your IP,
this is what is returned."""

_GENERIC_ERROR_RESPONSE = "-1"
"""General error response code. Could be as simple as "not found"."""


_SONG_ENDPOINT = "/getGJSongInfo.php"
"""The endpoint for Geometry Dash song information."""

_SFX_CDN_ENDPOINT = "/getCustomContentURL.php"
"""The endpoint for the CDN to the Geometry Dash songs library."""

_LOGGING_CONTENT_TRIM = 100
"""How many characters of the content should be stored in logs."""


def _is_response_valid(http_code: int, response: str) -> GDRequestStatus:
    """Classifies a response into a general request status.

    Note:
        Assumes `response` has already been stripped.
    """

    if http_code in range(500, 600):
        return GDRequestStatus.SERVER_ERROR

    elif response == _GENERIC_ERROR_RESPONSE:
        return GDRequestStatus.NOT_FOUND

    elif response == _ROBTOP_ERROR_RESPONSE:
        return GDRequestStatus.ROBTOP_BLACKLIST

    elif response == _CLOUDFLARE_ERROR_RESPONSE:
        return GDRequestStatus.CLOUDFLARE_ERROR

    return GDRequestStatus.NONE


type GDStatus[T] = T | GDRequestStatus
type IntKeyResponse = dict[int, str]


class BoomlingsSong(BaseModel):
    """A model representing a song response from """

    id: int
    name: str
    author_id: int
    author: str
    author_youtube: str | None
    size: float
    download_url: str

class BoomlingURL:
    """A class wrapping a URL retrieved from the Geometry Dash server.
    Used for typing convenience."""

    def __init__(self, url: str) -> None:
        self._url = url

    
    def url(self) -> str:
        return self._url

class GeometryDashClient:
    """A client for interacting with the Geometry Dash servers."""

    def __init__(
        self,
        server_url: str = GEOMETRY_DASH_URL,
        client_header: str = GEOMETRY_DASH_HEADER,
    ) -> None:
        self.server_url = server_url

        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": client_header,
            },
            timeout=2,
        )

    async def __make_post_request(
        self,
        endpoint: str,
        data: dict[str, Any] = {},
    ) -> GDStatus[str]:
        request_url = self.server_url + endpoint

        logger.debug(
            "Making a POST request to the Geometry Dash servers.",
            extra={
                "endpoint": endpoint,
            },
        )

        response = await self._client.post(
            request_url,
            data=data,
        )

        content = response.content.decode().strip()

        logger.debug(
            "POST request to Geometry Dash server succeeded.",
            extra={
                "endpoint": endpoint,
                "status_code": response.status_code,
                "content": content[:_LOGGING_CONTENT_TRIM],
            },
        )

        if (check := _is_response_valid(response.status_code, content)).is_error:
            return check

        return content

    # XXX: GD only has a **SINGLE** `GET` endpoint ANYWHERE in the protocol. Doesn't use data.
    async def __make_get_request(self, endpoint: str) -> GDStatus[str]:
        request_url = self.server_url + endpoint

        logger.debug(
            "Making a GET request to the Geometry Dash servers.",
            extra={
                "endpoint": endpoint,
            },
        )

        response = await self._client.get(
            request_url,
        )

        content = response.content.decode().strip()

        logger.debug(
            "GET request to Geometry Dash server succeeded.",
            extra={
                "endpoint": endpoint,
                "status_code": response.status_code,
                "content": content[:_LOGGING_CONTENT_TRIM],
            },
        )

        if (check := _is_response_valid(response.status_code, content)).is_error:
            return check

        return content

    async def song_from_id(self, song_id: int) -> GDStatus[BoomlingsSong]:
        """Queries the official servers for a song with a given id. Parses
        the response into a dictionary."""

        song_info = await self.__make_post_request(
            _SONG_ENDPOINT,
            # TODO: Is the secret necessary here?
            data={
                "songID": song_id,
                "secret": "Wmfd2893gb7",
            },
        )

        if isinstance(song_info, GDRequestStatus):
            if song_info.is_severe_error:
                logger.warning(
                    "Fetching song from the official servers failed with error.",
                    extra={
                        "song_id": song_id,
                        "error": song_info.value,
                    },
                )

            return song_info

        song_parsed = gd_obj.loads(
            song_info,
            sep="~|~",
            key_cast=int,
            value_cast=str,
        )

        # Creating model.
        return BoomlingsSong(
            id=int(song_parsed[1]),
            name=song_parsed[2],
            author_id=int(song_parsed[3]),
            author=song_parsed[4],
            author_youtube=song_parsed[7] or None,
            size=float(song_parsed[5]),
            download_url=unquote(song_parsed[10]),
        )

    async def fetch_cdn_id(self) -> GDStatus[BoomlingURL]:
        """Queries the official servers for the URL for the official Geometry Dash
        song and SFX library."""

        song_info = await self.__make_post_request(
            _SFX_CDN_ENDPOINT,
        )

        if isinstance(song_info, GDRequestStatus):
            if song_info.is_severe_error:
                logger.warning(
                    "Fetching the CDN from the official servers failed with error.",
                    extra={
                        "error": song_info.value,
                    },
                )

        # No parsing required here.
        return BoomlingURL(song_info)
