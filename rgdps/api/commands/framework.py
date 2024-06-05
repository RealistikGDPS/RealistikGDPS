from __future__ import annotations

import typing
from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from rgdps import logger
from rgdps import repositories
from rgdps.common.context import Context
from rgdps.constants.errors import ServiceError
from rgdps.constants.users import UserPrivileges
from rgdps.models.level import Level
from rgdps.models.rgb import RGB
from rgdps.models.user import User

if TYPE_CHECKING:
    from meilisearch_python_sdk import AsyncClient as MeiliClient
    from redis.asyncio import Redis

    from rgdps.common.cache.base import AbstractAsyncCache
    from rgdps.models.user import User
    from rgdps.adapters.boomlings import GeometryDashClient
    from rgdps.adapters.mysql import AbstractMySQLService
    from rgdps.adapters.storage import AbstractStorage


# Private parsing functions.
_CASTABLE = [
    str,
    int,
    float,
]
SupportedTypes = str | int | float | bool | Level | User | Enum


async def _level_by_ref(ctx: CommandContext, ref_value: str) -> Level:
    if ref_value.isnumeric():
        res = await repositories.level.from_id(
            ctx,
            int(ref_value),
        )
    else:
        res = await repositories.level.from_name(
            ctx,
            ref_value,
        )

    if res is None:
        raise ValueError("Could not find level from the given reference!")

    return res


async def _user_by_ref(ctx: CommandContext, ref_value: str) -> User:
    if ref_value.isnumeric():
        res = await repositories.user.from_id(
            ctx,
            int(ref_value),
        )

    else:
        res = await repositories.user.from_name(
            ctx,
            ref_value,
        )

    if res is None:
        raise ValueError("Could not find user from the given reference!")

    return res


def _unwrap_cast[T](cast: type[T]) -> type[T]:
    origin_type = get_origin(cast)
    origin_args = get_args(cast)

    # Handling for `T | None` types.
    if origin_type is Union and len(origin_args) == 2 and None in origin_args:
        return origin_args[1 - origin_args.index(None)]

    return cast


async def _resolve_from_type[T](ctx: CommandContext, value: str, cast: type[T]) -> T:
    cast = _unwrap_cast(cast)

    if cast in _CASTABLE:
        return cast(value)
    elif issubclass(cast, bool):
        return typing.cast(T, _bool_parse(value))
    elif issubclass(cast, RGB):
        return typing.cast(T, _rgb_parse(value))
    elif issubclass(cast, Level):
        return typing.cast(T, await _level_by_ref(ctx, value))
    elif issubclass(cast, User):
        return typing.cast(T, await _user_by_ref(ctx, value))
    elif issubclass(cast, Enum):
        return cast(value)

    logger.error(
        "Command parser tried to parse an unsupported type!",
        extra={
            "value": value,
            "type": repr(cast),
        },
    )
    raise ValueError(
        f"A resolver for the defined type {cast!r} has not been implemented!",
    )


def _bool_parse(data: str) -> bool:
    data = data.lower()
    if data in ("true", "1", "t"):
        return True
    elif data in ("false", "0", "f"):
        return False

    raise ValueError(f"Could not parse {data!r} as a boolean (true/false) value!")


def _rgb_parse(data: str) -> RGB:
    rgb = RGB.from_str(data)
    if rgb is not None:
        return rgb

    raise ValueError(f"Could not parse {data!r} as a RGB value!")


def _parse_params(param_str: str) -> list[str]:
    # TODO: maybe kwargs?
    if param_str.count('"') % 2 != 0:
        raise ValueError("Unclosed quotes in command parameters!")

    param_str = param_str.strip()
    if not param_str:
        raise ValueError("No command parameters provided!")

    quote_detection = param_str.split('"')
    # Issue if the last character is a quote, it will be an empty string.
    if param_str[-1] == '"':
        quote_detection = quote_detection[:-1]

    # All even indexes are outside quotes, all odd indexes are inside quotes.
    params = []
    for idx, value in enumerate(quote_detection):
        value = value.strip()
        if idx % 2 == 0:
            # Outside quotes, split by spaces.
            params.extend(value.split(" "))
        else:
            # Inside quotes, do not split.
            params.append(value)

    return params


async def _resolve_params(
    ctx: CommandContext,
    annotations: dict[str, Any],
    defaults: tuple[Any],
) -> list[Any]:
    params = []

    required_len = len(annotations) - len(defaults)
    max_len = len(annotations)
    provided_len = len(ctx.params)
    if provided_len < required_len or provided_len > max_len:
        raise ValueError(
            "Invalid number of parameters provided! Expected between "
            f"{required_len} and {max_len}, got {provided_len}!",
        )

    for arg_type, value in zip(annotations.values(), ctx.params):
        params.append(await _resolve_from_type(ctx, value, arg_type))

    return params


def _get_command_types(func: HandlerFunctionProtocol) -> dict[str, Any]:
    annotations = get_type_hints(func)

    return {
        key: value
        for key, value in annotations.items()
        if value is not CommandContext and key != "return"
    }


@dataclass
class CommandContext(Context):
    """A context object for command handlers, implementing the common
    `Context` API."""

    user: User
    # Cases for comment and message commands.
    level: Level | None
    target_user: User | None

    # Debugging details
    params: list[str]  # Prefix and name stripped.
    layer: CommandRoutable
    _base_context: Context

    @property
    def is_level(self) -> bool:
        return self.level is not None

    @property
    def is_message(self) -> bool:
        return self.target_user is not None

    # Implementation of context requirements
    @property
    def mysql(self) -> AbstractMySQLService:
        return self._base_context.mysql

    @property
    def redis(self) -> Redis:
        return self._base_context.redis

    @property
    def meili(self) -> MeiliClient:
        return self._base_context.meili

    @property
    def storage(self) -> AbstractStorage:
        return self._base_context.storage

    @property
    def password_cache(self) -> AbstractAsyncCache[str]:
        return self._base_context.password_cache

    @property
    def gd(self) -> GeometryDashClient:
        return self._base_context.gd


CommandEventHandler = Callable[[CommandContext], Awaitable[str]]
CommandErrorHandler = Callable[[CommandContext, Exception], Awaitable[str]]
CommandBareErrorHandler = Callable[[Exception], Awaitable[str]]
CommandConditional = Callable[[CommandContext], Awaitable[bool]]
CommandInfoHandler = Callable[[CommandContext, str], Awaitable[str]]
CommandMiscHandler = Callable[[], Awaitable[str]]


class CommandRoutable(ABC):
    """An abstract class defining interfaces that `CommandRouter` can use to
    execute commands."""

    name: str

    @abstractmethod
    async def execute(self, ctx: CommandContext) -> str: ...


class CommandException(Exception):
    """A user defined exception that can be raised in command handlers."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


# Default event handlers for routers.
async def _event_command_not_found(ctx: CommandContext, name: str) -> str:
    return f"Could not find a command with the name {name!r}!"


async def _event_invalid_format(exception: Exception) -> str:
    return (
        "Incorrect command format! Could not parse the given "
        f"input with error {exception}."
    )


async def _event_insufficient_conditions(ctx: CommandContext) -> str:
    return "Insufficient conditions to run this command!"


async def _event_misc_error() -> str:
    return "An internal error has occurred while executing this command!"


class CommandRouter(CommandRoutable):
    """An command router class, responible for registering and executing
    commands handlers. Supports nesting routers for command groups."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._routes: dict[str, CommandRoutable] = {}

        # Event handlers
        self._event_command_not_found: CommandInfoHandler = _event_command_not_found

        self._event_invalid_format: CommandBareErrorHandler = _event_invalid_format
        self._event_insufficient_conditions: CommandEventHandler = (
            _event_insufficient_conditions
        )
        self._event_misc_error: CommandMiscHandler = _event_misc_error

        self._execution_conditions: list[CommandConditional] = []

    def register_command(self, command: CommandRoutable) -> None:
        self._routes[command.name] = command

    def merge(self, router: CommandRouter) -> None:
        """Combines the routes of two routers, overriding old entries
        with new ones (raises a warning)."""

        for key, value in router._routes.items():
            if key in self._routes:
                logger.warning(
                    "Command router merge has overwritten an existing command!",
                    extra={
                        "command": key,
                        "source": router.name,
                        "target": self.name,
                    },
                )
            self._routes[key] = value

    def register(
        self,
    ) -> Callable[[CommandRoutable | type[CommandRoutable]], CommandRoutable]:
        """A decorator version of `register_command`."""

        def decorator(
            command: CommandRoutable | type[CommandRoutable],
        ) -> CommandRoutable:
            if isinstance(command, type):
                command = command()

            self.register_command(command)
            return command

        return decorator

    def register_function(
        self,
        name: str | None = None,
        description: str | None = None,
        required_privileges: UserPrivileges | None = None,
    ) -> Callable[[HandlerFunctionProtocol], CommandFunction]:
        def decorator(func: HandlerFunctionProtocol) -> CommandFunction:
            command = handler_as_command(
                func,
                name=name,
                description=description,
                required_privileges=required_privileges,
            )
            self.register_command(command)
            return command

        return decorator

    async def entrypoint(
        self,
        command: str,
        user: User,
        base_ctx: Context,
        level_id: int | None = None,
        target_user_id: int | None = None,
    ) -> str:
        """Defines an entrypoint for command execution. This method is
        supposed to be the first one called when executing a command."""

        try:
            parsed_params = _parse_params(command)
        except ValueError as e:
            return await self._event_invalid_format(e)

        command_name = parsed_params[0]

        # Resolve context details
        level = None
        if level_id is not None:
            level = await repositories.level.from_id(base_ctx, level_id)
            if level is None:
                logger.error(
                    "Failed to resolve the command level!",
                    extra={"level_id": level_id},
                )
                return await self._event_misc_error()

        target_user = None
        if target_user_id is not None:
            target_user = await repositories.user.from_id(base_ctx, target_user_id)
            if target_user is None:
                logger.error(
                    "Failed to resolve the command target user!",
                    extra={"target_user_id": target_user_id},
                )
                return await self._event_misc_error()

        ctx = CommandContext(
            user=user,
            level=level,
            target_user=target_user,
            params=parsed_params,
            _base_context=base_ctx,
            layer=self,
        )

        command_handler = self._routes.get(command_name)
        if command_handler is None:
            return await self._event_command_not_found(ctx, command_name)

        return await command_handler.execute(ctx)

    async def should_run(self, ctx: CommandContext) -> bool:
        """Function checking if all conditions for command execution
        are met."""

        # The list comprehension is required as we need to await
        return all([await condition(ctx) for condition in self._execution_conditions])

    async def execute(
        self,
        ctx: CommandContext,
    ) -> str:
        """Implements support for nesting routers."""

        ctx.layer = self
        ctx.params = ctx.params[1:]
        command_name = ctx.params[0]

        if not await self.should_run(ctx):
            return await self._event_insufficient_conditions(ctx)

        command_handler = self._routes.get(command_name)
        if command_handler is None:
            return await self._event_command_not_found(ctx, command_name)

        return await command_handler.execute(ctx)

    # Decorators for setting event handlers
    def on_command_not_found(
        self,
    ) -> Callable[[CommandInfoHandler], CommandInfoHandler]:
        """Decorator setting an event handler for whenever a command
        with the given name cannot be found."""

        def decorator(func: CommandInfoHandler) -> CommandInfoHandler:
            self._event_command_not_found = func
            return func

        return decorator

    def on_invalid_format(
        self,
    ) -> Callable[[CommandBareErrorHandler], CommandBareErrorHandler]:
        """Decorator setting an event handler for whenever malformed input
        is provided to a command."""

        def decorator(func: CommandBareErrorHandler) -> CommandBareErrorHandler:
            self._event_invalid_format = func
            return func

        return decorator

    def on_insufficient_conditions(
        self,
    ) -> Callable[[CommandEventHandler], CommandEventHandler]:
        """Decorator setting an event handler for whenever a command's
        custom defined pre-requisites are not met."""

        def decorator(func: CommandEventHandler) -> CommandEventHandler:
            self._event_insufficient_conditions = func
            return func

        return decorator

    def on_misc_error(
        self,
    ) -> Callable[[CommandMiscHandler], CommandMiscHandler]:
        """Decorator setting an event handler for whenever a misc error
        that does not concern the user occurs."""

        def decorator(func: CommandMiscHandler) -> CommandMiscHandler:
            self._event_misc_error = func
            return func

        return decorator

    def execution_condition(
        self,
    ) -> Callable[[CommandConditional], CommandConditional]:
        """Decorator adding a condition that must be met for the command
        to be executed. May be used multiple times."""

        def decorator(func: CommandConditional) -> CommandConditional:
            self._execution_conditions.append(func)
            return func

        return decorator


# Command specific event handlers
async def _event_on_exception(ctx: CommandContext, exception: Exception) -> str:
    logger.exception(
        "An exception has occurred while executing command!",
        extra={
            "command_name": ctx.layer.name,
            "command_input": ctx.params,
            "user_id": ctx.user.id,
        },
        exc_info=exception,
    )
    return (
        "An exeption has occurred while executing this command! "
        "The developers have been notified."
    )


async def _event_insufficient_privileges(ctx: CommandContext) -> str:
    return "You have insufficient privileges to run this command."


async def _event_invalid_arguments(ctx: CommandContext, exception: Exception) -> str:
    return "Matching the given command arguments has failed with error " + str(
        exception,
    )


async def _event_interruption(ctx: CommandContext, exception: Exception) -> str:
    return "The command has been interrupted with error " + str(exception)


class Command(CommandRoutable):
    """Inheritable command structure for implementing custom commands."""

    def __init__(
        self,
        name: str,
        description: str,
        required_privileges: UserPrivileges | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.required_privileges = required_privileges

        if self.required_privileges:
            self.required_privileges |= UserPrivileges.COMMANDS_TRIGGER

        # Event handlers
        self._event_on_exception: CommandErrorHandler = _event_on_exception
        self._event_insufficient_privileges: CommandEventHandler = (
            _event_insufficient_privileges
        )
        self._event_invalid_arguments: CommandErrorHandler = _event_invalid_arguments
        self._event_insufficient_conditions: CommandEventHandler = (
            _event_insufficient_conditions
        )
        self._event_interruption: CommandErrorHandler = _event_interruption
        self._execution_conditions: list[CommandConditional] = []

    async def handle(self, ctx: CommandContext) -> str:
        """Default command handler. May be overridden by subclasses."""

        return "Hello, world!"

    async def should_run(self, ctx: CommandContext) -> bool:
        """Checks if all defined execution criteria has been met."""

        # The list comprehension is required as we need to await
        return all([await condition(ctx) for condition in self._execution_conditions])

    async def execute(self, ctx: CommandContext) -> str:
        """Called by the command router to perform command checks and execution."""

        ctx.layer = self
        # Modify params to remove the command name.
        ctx.params = ctx.params[1:]

        if not self.__has_privileges(ctx):
            return await self._event_insufficient_privileges(ctx)

        if not await self.should_run(ctx):
            return await self._event_insufficient_conditions(ctx)

        try:
            params = await self._parse_params(ctx)
        except ValueError as e:
            return await self._event_invalid_arguments(ctx, e)

        try:
            result = await self.handle(ctx, *params)
            logger.info(
                "Successfully executed command!",
                extra={
                    "command_name": self.name,
                    "user_id": ctx.user.id,
                },
            )
            return result
        except CommandException as e:
            return await self._event_interruption(ctx, e)
        except Exception as e:
            logger.exception(
                "Failed to run command handler!",
                extra={
                    "command_name": self.name,
                    "command_input": ctx.params,
                    "user_id": ctx.user.id,
                },
            )
            return await self._event_on_exception(ctx, e)

    # Private API
    def __has_privileges(self, ctx: CommandContext) -> bool:
        if self.required_privileges:
            return (
                ctx.user.privileges & self.required_privileges
            ) == self.required_privileges

        return True

    async def _parse_params(self, ctx: CommandContext) -> list[Any]:
        annotations = _get_command_types(self.handle)
        default_params = self.handle.__defaults__ or ()
        return await _resolve_params(ctx, annotations, default_params)  # type: ignore

    # Decorators
    def on_exception(
        self,
    ) -> Callable[[CommandErrorHandler], CommandErrorHandler]:
        """Decorator setting an event handler for whenever an exception
        occurs during command execution."""

        def decorator(func: CommandErrorHandler) -> CommandErrorHandler:
            self._event_on_exception = func
            return func

        return decorator

    def on_insufficient_privileges(
        self,
    ) -> Callable[[CommandEventHandler], CommandEventHandler]:
        """Decorator setting an event handler for whenever a user attempts
        to execute a command without sufficient privileges."""

        def decorator(func: CommandEventHandler) -> CommandEventHandler:
            self._event_insufficient_privileges = func
            return func

        return decorator

    def on_invalid_arguments(
        self,
    ) -> Callable[[CommandErrorHandler], CommandErrorHandler]:
        """Decorator setting an event handler for whenever a user attempts
        to execute a command with invalid arguments."""

        def decorator(func: CommandErrorHandler) -> CommandErrorHandler:
            self._event_invalid_arguments = func
            return func

        return decorator

    def on_insufficient_conditions(
        self,
    ) -> Callable[[CommandEventHandler], CommandEventHandler]:
        """Decorator setting an event handler for whenever a user attempts
        to execute a command without meeting the custom execution criteria."""

        def decorator(func: CommandEventHandler) -> CommandEventHandler:
            self._event_insufficient_conditions = func
            return func

        return decorator

    def on_interruption(
        self,
    ) -> Callable[[CommandErrorHandler], CommandErrorHandler]:
        """Decorator setting an event handler for whenever a `CommandException`
        is raised during command execution."""

        def decorator(func: CommandErrorHandler) -> CommandErrorHandler:
            self._event_interruption = func
            return func

        return decorator

    def execution_condition(
        self,
    ) -> Callable[[CommandConditional], CommandConditional]:
        """Decorator adding a condition that must be met for the command
        to be executed. May be used multiple times."""

        def decorator(func: CommandConditional) -> CommandConditional:
            self._execution_conditions.append(func)
            return func

        return decorator


# class HandlerFunctionProtocol(Protocol):
#    """A protocol for defining a command handler function."""
#
#    __name__: str
#    __defaults__: tuple[Any, ...] | None
#
#    async def __call__(self, ctx: CommandContext, *args: Any) -> str:
#        ...

HandlerFunctionProtocol = Callable[..., Awaitable[str]]


class CommandFunction(Command):
    """A child class of `Command` that allows for defining an entire command
    in a single function. Used for simple commands that do not require
    a lot of boilerplate or custom functionality."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: HandlerFunctionProtocol,
        required_privileges: UserPrivileges | None = None,
    ) -> None:
        super().__init__(name, description, required_privileges)
        self._handler = handler

    async def handle(self, ctx: CommandContext, *args: SupportedTypes) -> str:
        return await self._handler(ctx, *args)

    async def _parse_params(self, ctx: CommandContext) -> list[Any]:
        annotations = _get_command_types(self._handler)
        default_params = self._handler.__defaults__ or ()
        return await _resolve_params(ctx, annotations, default_params)  # type: ignore


class UnparsedCommand(Command):
    """A child class of `Command` that bypasses the annotation-based
    command parsing and passes the raw string arguments to the command handler
    as a single string."""

    async def _parse_params(self, ctx: CommandContext) -> list[Any]:
        return [" ".join(ctx.params)]


def handler_as_command(
    handler: HandlerFunctionProtocol,
    name: str | None = None,
    description: str | None = None,
    required_privileges: UserPrivileges | None = None,
) -> CommandFunction:
    """Creates an instance of `CommandFunction` from a handler function and its
    signature."""

    command_name = name or handler.__name__
    command_description = description or handler.__doc__ or ""

    return CommandFunction(
        command_name,
        command_description,
        handler,
        required_privileges,
    )


def make_command(
    name: str | None = None,
    description: str | None = None,
    required_privileges: UserPrivileges | None = None,
) -> Callable[[HandlerFunctionProtocol], CommandFunction]:
    """A decorator for defining a command in a single function.
    Creates an instance of `CommandFunction` with the provided arguments,
    or tries to work them out from the function name and docstring.
    The decorator equivalent of `handler_as_command`."""

    def decorator(handler: HandlerFunctionProtocol) -> CommandFunction:
        return handler_as_command(
            handler,
            name,
            description,
            required_privileges,
        )

    return decorator


def unwrap_service[T](value: T | ServiceError) -> T:
    """Raises a `CommandExcpetion` interrupt if a usecase returns a service error."""

    if isinstance(value, ServiceError):
        raise CommandException(value.value)

    return value
