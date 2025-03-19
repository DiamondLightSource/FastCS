from collections.abc import Callable, Coroutine
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import create_model

from fastcs.attributes import AttrR, AttrRW, AttrW, T
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import CommandCallback

from .options import RestServerOptions
from .util import (
    cast_from_rest_type,
    cast_to_rest_type,
    convert_datatype,
)


class RestServer:
    """A Rest Server which handles a controller.

    Avoid running directly, instead use `fastcs.launch.FastCS`.
    """

    def __init__(self, controller_api: ControllerAPI):
        self._controller_api = controller_api
        self._app = self._create_app()

    def _create_app(self):
        app = FastAPI()
        _add_attribute_api_routes(app, self._controller_api)
        _add_command_api_routes(app, self._controller_api)

        return app

    async def serve(self, options: RestServerOptions | None):
        options = options or RestServerOptions()
        self._server = uvicorn.Server(
            uvicorn.Config(
                app=self._app,
                host=options.host,
                port=options.port,
                log_level=options.log_level,
            )
        )
        await self._server.serve()


def _put_request_body(attribute: AttrW[T]):
    """
    Creates a pydantic model for each datatype which defines the schema
    of the PUT request body
    """
    converted_datatype = convert_datatype(attribute.datatype)
    type_name = str(attribute.datatype.dtype.__name__).title()
    # key=(type, ...) to declare a field without default value
    return create_model(
        f"Put{type_name}Value",
        value=(converted_datatype, ...),
    )


def _wrap_attr_put(
    attribute: AttrW[T],
) -> Callable[[T], Coroutine[Any, Any, None]]:
    async def attr_set(request):
        await attribute.process(cast_from_rest_type(attribute.datatype, request.value))

    # Fast api uses type annotations for validation, schema, conversions
    attr_set.__annotations__["request"] = _put_request_body(attribute)

    return attr_set


def _get_response_body(attribute: AttrR[T]):
    """
    Creates a pydantic model for each datatype which defines the schema
    of the GET request body
    """
    converted_datatype = convert_datatype(attribute.datatype)
    type_name = str(converted_datatype.__name__).title()
    # key=(type, ...) to declare a field without default value
    return create_model(
        f"Get{type_name}Value",
        value=(converted_datatype, ...),
    )


def _wrap_attr_get(
    attribute: AttrR[T],
) -> Callable[[], Coroutine[Any, Any, Any]]:
    async def attr_get() -> Any:  # Must be any as response_model is set
        value = attribute.get()  # type: ignore
        return {"value": cast_to_rest_type(attribute.datatype, value)}

    return attr_get


def _add_attribute_api_routes(app: FastAPI, root_controller_api: ControllerAPI) -> None:
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path

        for attr_name, attribute in controller_api.attributes.items():
            attr_name = attr_name.replace("_", "-")
            route = f"{'/'.join(path)}/{attr_name}" if path else attr_name

            match attribute:
                # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
                case AttrRW():
                    app.add_api_route(
                        f"/{route}",
                        _wrap_attr_get(attribute),
                        methods=["GET"],  # Idempotent and safe data retrieval,
                        status_code=200,  # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET
                        response_model=_get_response_body(attribute),
                    )
                    app.add_api_route(
                        f"/{route}",
                        _wrap_attr_put(attribute),
                        methods=["PUT"],  # Idempotent state change
                        status_code=204,  # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PUT
                    )
                case AttrR():
                    app.add_api_route(
                        f"/{route}",
                        _wrap_attr_get(attribute),
                        methods=["GET"],
                        status_code=200,
                        response_model=_get_response_body(attribute),
                    )
                case AttrW():
                    app.add_api_route(
                        f"/{route}",
                        _wrap_attr_put(attribute),
                        methods=["PUT"],
                        status_code=204,
                    )


def _wrap_command(
    method: CommandCallback,
) -> Callable[..., Coroutine[None, None, None]]:
    async def command() -> None:
        await method()

    return command


def _add_command_api_routes(app: FastAPI, root_controller_api: ControllerAPI) -> None:
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path

        for name, method in root_controller_api.command_methods.items():
            cmd_name = name.replace("_", "-")
            route = f"/{'/'.join(path)}/{cmd_name}" if path else cmd_name
            app.add_api_route(
                f"/{route}",
                _wrap_command(method.fn),
                methods=["PUT"],
                status_code=204,
            )
