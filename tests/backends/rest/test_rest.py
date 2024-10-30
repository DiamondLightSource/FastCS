import copy
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fastcs.attributes import AttrR
from fastcs.backends.rest.backend import RestBackend
from fastcs.datatypes import Bool, Float, Int


def pascal_2_snake(input: list[str]) -> list[str]:
    snake_list = copy.deepcopy(input)
    snake_list[-1] = re.sub(r"(?<!^)(?=[A-Z])", "_", snake_list[-1]).lower()
    return snake_list


class TestRestServer:
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, assertable_controller):
        self.controller = assertable_controller

    @pytest.fixture(scope="class")
    def client(self):
        app = RestBackend(self.controller)._server._app
        return TestClient(app)

    @pytest.fixture(scope="class")
    def client_read(self, client):
        def _client_read(path: list[str], expected: Any):
            route = "/" + "/".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "READ"):
                response = client.get(route)
            assert response.status_code == 200
            assert response.json()["value"] == expected

        return _client_read

    @pytest.fixture(scope="class")
    def client_write(self, client):
        def _client_write(path: list[str], value: Any):
            route = "/" + "/".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "WRITE"):
                response = client.put(route, json={"value": value})
            assert response.status_code == 204

        return _client_write

    @pytest.fixture(scope="class")
    def client_exec(self, client):
        def _client_exec(path: list[str]):
            route = "/" + "/".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "EXECUTE"):
                response = client.put(route)
            assert response.status_code == 204

        return _client_exec

    def test_read_int(self, client_read):
        client_read(["ReadInt"], AttrR(Int())._value)

    def test_read_write_int(self, client_read, client_write):
        client_read(["ReadWriteInt"], AttrR(Int())._value)
        client_write(["ReadWriteInt"], AttrR(Int())._value)

    def test_read_write_float(self, client_read, client_write):
        client_read(["ReadWriteFloat"], AttrR(Float())._value)
        client_write(["ReadWriteFloat"], AttrR(Float())._value)

    def test_read_bool(self, client_read):
        client_read(["ReadBool"], AttrR(Bool())._value)

    def test_write_bool(self, client_write):
        client_write(["WriteBool"], AttrR(Bool())._value)

    # # We need to discuss enums
    # def test_string_enum(self, client_read, client_write):

    def test_big_enum(self, client_read):
        client_read(["BigEnum"], AttrR(Int(), allowed_values=list(range(1, 18)))._value)

    def test_go(self, client_exec):
        client_exec(["Go"])

    def test_read_child1(self, client_read):
        client_read(["SubController01", "ReadInt"], AttrR(Int())._value)

    def test_read_child2(self, client_read):
        client_read(["SubController02", "ReadInt"], AttrR(Int())._value)
