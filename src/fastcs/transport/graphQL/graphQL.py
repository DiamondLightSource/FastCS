from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import strawberry
import uvicorn
from strawberry.asgi import GraphQL
from strawberry.tools import create_type
from strawberry.types.field import StrawberryField

from fastcs.attributes import AttrR, AttrRW, AttrW, T
from fastcs.controller import BaseController, Controller

from .options import GraphQLServerOptions


class GraphQLServer:
    def __init__(self, controller: Controller):
        self._controller = controller
        self._fields_tree: FieldTree = FieldTree("")
        self._app = self._create_app()

    def _create_app(self) -> GraphQL:
        _add_attribute_operations(self._fields_tree, self._controller)
        _add_command_mutations(self._fields_tree, self._controller)

        schema_kwargs = {}
        for key in ["query", "mutation"]:
            if s_type := self._fields_tree.create_strawberry_type(key):
                schema_kwargs[key] = s_type
        schema = strawberry.Schema(**schema_kwargs)  # type: ignore
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


def _wrap_attr_set(
    attr_name: str,
    attribute: AttrW[T],
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
    attr_name: str,
    attribute: AttrR[T],
) -> Callable[[], Coroutine[Any, Any, Any]]:
    async def _dynamic_f() -> Any:
        return attribute.get()

    _dynamic_f.__name__ = attr_name
    _dynamic_f.__annotations__["return"] = attribute.datatype.dtype

    return _dynamic_f


def _wrap_as_field(
    field_name: str,
    strawberry_type: type,
) -> StrawberryField:
    def _dynamic_field():
        return strawberry_type()

    _dynamic_field.__name__ = field_name
    _dynamic_field.__annotations__["return"] = strawberry_type

    return strawberry.field(_dynamic_field)


class FieldTree:
    def __init__(self, name: str):
        self.name = name
        self.children: dict[str, FieldTree] = {}
        self.fields: dict[str, list[StrawberryField]] = {
            "query": [],
            "mutation": [],
        }

    def insert(self, path: list[str]) -> "FieldTree":
        # Create child if not exist
        name = path.pop(0)
        if child := self.get_child(name):
            pass
        else:
            child = FieldTree(name)
            self.children[name] = child

        # Recurse if needed
        if path:
            return child.insert(path)
        else:
            return child

    def get_child(self, name: str) -> "FieldTree | None":
        if name in self.children:
            return self.children[name]
        else:
            return None

    def create_strawberry_type(self, strawberry_type: str) -> type | None:
        for child in self.children.values():
            if new_type := child.create_strawberry_type(strawberry_type):
                child_field = _wrap_as_field(
                    child.name,
                    new_type,
                )
                self.fields[strawberry_type].append(child_field)

        if self.fields[strawberry_type]:
            return create_type(
                f"{self.name}{strawberry_type}", self.fields[strawberry_type]
            )
        else:
            return None


def _add_attribute_operations(
    fields_tree: FieldTree,
    controller: Controller,
) -> None:
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        if path:
            node = fields_tree.insert(path)
        else:
            node = fields_tree

        if node is not None:
            for attr_name, attribute in single_mapping.attributes.items():
                match attribute:
                    # mutation for server changes https://graphql.org/learn/queries/
                    case AttrRW():
                        node.fields["query"].append(
                            strawberry.field(_wrap_attr_get(attr_name, attribute))
                        )
                        node.fields["mutation"].append(
                            strawberry.mutation(_wrap_attr_set(attr_name, attribute))
                        )
                    case AttrR():
                        node.fields["query"].append(
                            strawberry.field(_wrap_attr_get(attr_name, attribute))
                        )
                    case AttrW():
                        node.fields["mutation"].append(
                            strawberry.mutation(_wrap_attr_set(attr_name, attribute))
                        )


def _wrap_command(
    method_name: str, method: Callable, controller: BaseController
) -> Callable[..., Awaitable[bool]]:
    async def _dynamic_f() -> bool:
        await getattr(controller, method.__name__)()
        return True

    _dynamic_f.__name__ = method_name

    return _dynamic_f


def _add_command_mutations(fields_tree: FieldTree, controller: Controller) -> None:
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        if path:
            node = fields_tree.insert(path)
        else:
            node = fields_tree

        if node is not None:
            for cmd_name, method in single_mapping.command_methods.items():
                node.fields["mutation"].append(
                    strawberry.mutation(
                        _wrap_command(
                            cmd_name,
                            method.fn,
                            single_mapping.controller,
                        )
                    )
                )
