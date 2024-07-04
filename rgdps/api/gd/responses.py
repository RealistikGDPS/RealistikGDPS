from __future__ import annotations

from typing import NoReturn

from fastapi.responses import PlainTextResponse
from fastapi import HTTPException

from rgdps.common.typing import SupportsStr
from rgdps.constants.responses import GenericResponse
from rgdps.services import ServiceError
from rgdps.services import ErrorOr

_SERVEICE_ERROR_CODE_MAP = {
    ServiceError.USER_USERNAME_EXISTS: -2,
}
"""A map linking a Service Error to its corresponding GD error code."""

def _resolve_error_from_service_error(service_error: ServiceError) -> int:
    return _SERVEICE_ERROR_CODE_MAP.get(service_error, -1)

def interrupt_with_error(error: SupportsStr) -> NoReturn:
    """Interrupts the HTTP execution with the given error code."""

    raise HTTPException(
        status_code=200,
        detail=str(error),
    )


def unwrap[T](value: ErrorOr[T]) -> T:
    """Unwraps a service response. Returns the value if given unchanged.
    Else, interrupts HTTP execution."""

    if isinstance(value, ServiceError):
        interrupt_with_error(
            _resolve_error_from_service_error(value)
        )

    return value


def success() -> PlainTextResponse:
    return PlainTextResponse(str(GenericResponse.SUCCESS))


def fail() -> PlainTextResponse:
    return PlainTextResponse(str(GenericResponse.FAIL))


def code(code: SupportsStr) -> PlainTextResponse:
    return PlainTextResponse(str(code))
