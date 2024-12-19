import copy
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from tests.assertable_controller import (
    AssertableController,
    TestHandler,
    TestSender,
    TestUpdater,
)

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.transport.graphQL.adapter import GraphQLTransport


class RestAssertableController(AssertableController):
    read_int = AttrR(Int(), handler=TestUpdater())
    read_write_int = AttrRW(Int(), handler=TestHandler())
    read_write_float = AttrRW(Float())
    read_bool = AttrR(Bool())
    write_bool = AttrW(Bool(), handler=TestSender())
    read_string = AttrRW(String())
    big_enum = AttrR(
        Int(
            allowed_values=list(range(17)),
        ),
    )


@pytest.fixture(scope="class")
def assertable_controller(class_mocker: MockerFixture):
    return RestAssertableController(class_mocker)


def nest_query(path: list[str]) -> str:
    queue = copy.deepcopy(path)
    field = queue.pop(0)

    if queue:
        nesting = nest_query(queue)
        return f"{field} {{ {nesting} }} "
    else:
        return field


def nest_mutation(path: list[str], value: Any) -> str:
    queue = copy.deepcopy(path)
    field = queue.pop(0)

    if queue:
        nesting = nest_query(queue)
        return f"{field} {{ {nesting} }} "
    else:
        return f"{field}(value: {json.dumps(value)})"


def nest_responce(path: list[str], value: Any) -> dict:
    queue = copy.deepcopy(path)
    field = queue.pop(0)

    if queue:
        nesting = nest_responce(queue, value)
        return {field: nesting}
    else:
        return {field: value}


class TestGraphQLServer:
    @pytest.fixture(scope="class")
    def client(self, assertable_controller):
        app = GraphQLTransport(
            assertable_controller,
        )._server._app
        return TestClient(app)

    def test_read_int(self, client, assertable_controller):
        expect = 0
        path = ["readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_read_write_int(self, client, assertable_controller):
        expect = 0
        path = ["readWriteInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_write_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

        new = 9
        mutation = f"mutation {{ {nest_mutation(path, new)} }}"
        with assertable_controller.assert_write_here(["read_write_int"]):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, new)

    def test_read_write_float(self, client, assertable_controller):
        expect = 0
        path = ["readWriteFloat"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_write_float"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

        new = 0.5
        mutation = f"mutation {{ {nest_mutation(path, new)} }}"
        with assertable_controller.assert_write_here(["read_write_float"]):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, new)

    def test_read_bool(self, client, assertable_controller):
        expect = False
        path = ["readBool"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_bool"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_write_bool(self, client, assertable_controller):
        value = True
        path = ["writeBool"]
        mutation = f"mutation {{ {nest_mutation(path, value)} }}"
        with assertable_controller.assert_write_here(["write_bool"]):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, value)

    def test_big_enum(self, client, assertable_controller):
        expect = 0
        path = ["bigEnum"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["big_enum"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_go(self, client, assertable_controller):
        path = ["go"]
        mutation = f"mutation {{ {nest_query(path)} }}"
        with assertable_controller.assert_execute_here(path):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == {path[-1]: True}

    def test_read_child1(self, client, assertable_controller):
        expect = 0
        path = ["SubController01", "readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["SubController01", "read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_read_child2(self, client, assertable_controller):
        expect = 0
        path = ["SubController02", "readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["SubController02", "read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)
