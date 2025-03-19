from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import strawberry
import uvicorn
from strawberry.asgi import GraphQL
from strawberry.tools import create_type
from strawberry.types.field import StrawberryField

from fastcs.attributes import AttrR, AttrRW, AttrW, T
from fastcs.controller_api import ControllerAPI
from fastcs.exceptions import FastCSException

from .options import GraphQLServerOptions


class GraphQLServer:
    """A GraphQL server which handles a controller.

    Avoid running directly, instead use `fastcs.launch.FastCS`.
    """

    def __init__(self, controller_api: ControllerAPI):
        self._controller_api = controller_api
        self._app = self._create_app()

    def _create_app(self) -> GraphQL:
        api = GraphQLAPI(self._controller_api)
        schema = api.create_schema()
        app = GraphQL(schema)

        return app

    async def serve(self, options: GraphQLServerOptions | None = None) -> None:
        options = options or GraphQLServerOptions()
        self._server = uvicorn.Server(
            uvicorn.Config(
                app=self._app,
                host=options.host,
                port=options.port,
                log_level=options.log_level,
            )
        )
        await self._server.serve()


class GraphQLAPI:
    """A Strawberry API built dynamically from a `ControllerAPI`"""

    def __init__(self, controller_api: ControllerAPI):
        self.queries: list[StrawberryField] = []
        self.mutations: list[StrawberryField] = []

        self._process_attributes(controller_api)
        self._process_commands(controller_api)
        self._process_sub_apis(controller_api)

    def _process_attributes(self, api: ControllerAPI):
        """Create queries and mutations from api attributes."""
        for attr_name, attribute in api.attributes.items():
            match attribute:
                # mutation for server changes https://graphql.org/learn/queries/
                case AttrRW():
                    self.queries.append(
                        strawberry.field(_wrap_attr_get(attr_name, attribute))
                    )
                    self.mutations.append(
                        strawberry.mutation(_wrap_attr_set(attr_name, attribute))
                    )
                case AttrR():
                    self.queries.append(
                        strawberry.field(_wrap_attr_get(attr_name, attribute))
                    )
                case AttrW():
                    self.mutations.append(
                        strawberry.mutation(_wrap_attr_set(attr_name, attribute))
                    )

    def _process_commands(self, controller_api: ControllerAPI):
        """Create mutations from api commands"""
        for name, method in controller_api.command_methods.items():
            self.mutations.append(strawberry.mutation(_wrap_command(name, method.fn)))

    def _process_sub_apis(self, root_controller_api: ControllerAPI):
        """Recursively add fields from the queries and mutations of sub apis"""
        for controller_api in root_controller_api.sub_apis.values():
            name = "".join(controller_api.path)
            child_tree = GraphQLAPI(controller_api)
            if child_tree.queries:
                self.queries.append(
                    _wrap_as_field(
                        name, create_type(f"{name}Query", child_tree.queries)
                    )
                )
            if child_tree.mutations:
                self.mutations.append(
                    _wrap_as_field(
                        name, create_type(f"{name}Mutation", child_tree.mutations)
                    )
                )

    def create_schema(self) -> strawberry.Schema:
        """Create a Strawberry Schema to load into a GraphQL application."""
        if not self.queries:
            raise FastCSException(
                "Can't create GraphQL transport from ControllerAPI with no read "
                "attributes"
            )

        query = create_type("Query", self.queries)
        mutation = create_type("Mutation", self.mutations) if self.mutations else None

        return strawberry.Schema(query=query, mutation=mutation)


def _wrap_attr_set(
    attr_name: str, attribute: AttrW[T]
) -> Callable[[T], Coroutine[Any, Any, None]]:
    """Wrap an attribute in a function with annotations for strawberry"""

    async def _dynamic_f(value):
        await attribute.process(value)
        return value

    # Add type annotations for validation, schema, conversions
    _dynamic_f.__name__ = attr_name
    _dynamic_f.__annotations__["value"] = attribute.datatype.dtype
    _dynamic_f.__annotations__["return"] = attribute.datatype.dtype

    return _dynamic_f


def _wrap_attr_get(
    attr_name: str, attribute: AttrR[T]
) -> Callable[[], Coroutine[Any, Any, Any]]:
    """Wrap an attribute in a function with annotations for strawberry"""

    async def _dynamic_f() -> Any:
        return attribute.get()

    _dynamic_f.__name__ = attr_name
    _dynamic_f.__annotations__["return"] = attribute.datatype.dtype

    return _dynamic_f


def _wrap_as_field(field_name: str, operation: type) -> StrawberryField:
    """Wrap a strawberry type as a field of a parent type"""

    def _dynamic_field():
        return operation()

    _dynamic_field.__name__ = field_name
    _dynamic_field.__annotations__["return"] = operation

    return strawberry.field(_dynamic_field)


def _wrap_command(method_name: str, method: Callable) -> Callable[..., Awaitable[bool]]:
    """Wrap a command in a function with annotations for strawberry"""

    async def _dynamic_f() -> bool:
        await method()
        return True

    _dynamic_f.__name__ = method_name

    return _dynamic_f
