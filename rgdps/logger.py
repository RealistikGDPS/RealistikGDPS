from __future__ import annotations

import logging.config
import sys
import threading
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Optional


LOGGER = logging.getLogger("rgdps")


def init_basic_logging(log_level: str | int) -> None:
    logging.basicConfig(level=log_level)
    hook_exception_handlers()

def debug(*args, **kwargs) -> None:
    return LOGGER.debug(*args, **kwargs)


def info(*args, **kwargs) -> None:
    return LOGGER.info(*args, **kwargs)


def warning(*args, **kwargs) -> None:
    return LOGGER.warning(*args, **kwargs)


def error(*args, **kwargs) -> None:
    return LOGGER.error(*args, **kwargs)


def critical(*args, **kwargs) -> None:
    return LOGGER.critical(*args, **kwargs)


def exception(*args, **kwargs) -> None:
    return LOGGER.exception(*args, **kwargs)


# Hooking the exception handler to log uncaught exceptions.
# https://gist.github.com/cmyui/201f3d687d289f24a3357c9ff3302206
# NOTE: Decouple if needed.
ExceptionHook = Callable[
    [type[BaseException], BaseException, Optional[TracebackType]],
    Any,
]
ThreadingExceptionHook = Callable[[threading.ExceptHookArgs], Any]

_default_excepthook: Optional[ExceptionHook] = None
_default_threading_excepthook: Optional[ThreadingExceptionHook] = None


# NOTE: This doesn't work on Uvicorn because it uses its own exception handler.
# There has been an equivalent exception hook added on the FastAPI level.
def internal_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: Optional[TracebackType],
) -> Any:
    LOGGER.exception(
        "An unhandled exception occurred!",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def internal_thread_exception_handler(
    args: threading.ExceptHookArgs,
) -> Any:
    if args.exc_value is not None:
        LOGGER.exception(
            "An unhandled exception occurred!",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            extra={"thread_vars": vars(args.thread)},
        )
    else:
        LOGGER.warning(
            "A thread exception hook was called without an exception value!",
            extra={
                "exc_type": args.exc_type,
                "exc_value": args.exc_value,
                "exc_traceback": args.exc_traceback,
                "thread_vars": vars(args.thread),
            },
        )


def hook_exception_handlers() -> None:
    global _default_excepthook
    _default_excepthook = sys.excepthook
    sys.excepthook = internal_exception_handler

    global _default_threading_excepthook
    _default_threading_excepthook = threading.excepthook
    threading.excepthook = internal_thread_exception_handler


def unhook_exception_handlers() -> None:
    global _default_excepthook
    if _default_excepthook is not None:
        sys.excepthook = _default_excepthook

    global _default_threading_excepthook
    if _default_threading_excepthook is not None:
        threading.excepthook = _default_threading_excepthook
