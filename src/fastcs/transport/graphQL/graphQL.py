from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import strawberry
import uvicorn
from strawberry.asgi import GraphQL
from strawberry.tools import create_type
from strawberry.types.field import StrawberryField

from fastcs.attributes import AttrR, AttrRW, AttrW, T
from fastcs.controller import BaseController, Controller, _get_single_mapping

from .options import GraphQLServerOptions


class GraphQLServer:
    def __init__(self, controller: Controller):
        self._controller = controller
        self._app = self._create_app()

    def _create_app(self) -> GraphQL:
        api = GraphQLAPI(self._controller)

        if not api.queries:
            raise ValueError(
                "Can't create GraphQL transport from Controller with no read attributes"
            )

        mutation = create_type("Mutation", api.mutations) if api.mutations else None
        schema = strawberry.Schema(
            query=create_type("Query", api.queries), mutation=mutation
        )
        app = GraphQL(schema)

        return app

    def run(self, options: GraphQLServerOptions | None = None) -> None:
        if options is None:
            options = GraphQLServerOptions()

        uvicorn.run(
            self._app,
            host=options.host,
            port=options.port,
            log_level=options.log_level,
        )


class GraphQLAPI:
    """A Strawberry API built dynamically from a Controller"""

    def __init__(self, controller: BaseController):
        self.queries: list[StrawberryField] = []
        self.mutations: list[StrawberryField] = []

        api = _get_single_mapping(controller)

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

        for cmd_name, method in api.command_methods.items():
            self.mutations.append(
                strawberry.mutation(_wrap_command(cmd_name, method.fn, controller))
            )

        for sub_controller in controller.get_sub_controllers().values():
            name = "".join(sub_controller.path)
            child_tree = GraphQLAPI(sub_controller)
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


def _wrap_attr_set(
    attr_name: str, attribute: AttrW[T]
) -> Callable[[T], Coroutine[Any, Any, None]]:
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
    async def _dynamic_f() -> Any:
        return attribute.get()

    _dynamic_f.__name__ = attr_name
    _dynamic_f.__annotations__["return"] = attribute.datatype.dtype

    return _dynamic_f


def _wrap_as_field(field_name: str, operation: type) -> StrawberryField:
    def _dynamic_field():
        return operation()

    _dynamic_field.__name__ = field_name
    _dynamic_field.__annotations__["return"] = operation

    return strawberry.field(_dynamic_field)


def _wrap_command(
    method_name: str, method: Callable, controller: BaseController
) -> Callable[..., Awaitable[bool]]:
    async def _dynamic_f() -> bool:
        await getattr(controller, method.__name__)()
        return True

    _dynamic_f.__name__ = method_name

    return _dynamic_f
