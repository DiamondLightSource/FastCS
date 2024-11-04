import copy
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fastcs.transport.graphQL.adapter import GraphQLTransport


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
        app = GraphQLTransport(assertable_controller)._server._app
        return TestClient(app)

    def test_read_int(self, assertable_controller, client):
        expect = 0
        path = ["readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_read_write_int(self, assertable_controller, client):
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

    def test_read_write_float(self, assertable_controller, client):
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

    def test_read_bool(self, assertable_controller, client):
        expect = False
        path = ["readBool"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["read_bool"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_write_bool(self, assertable_controller, client):
        value = True
        path = ["writeBool"]
        mutation = f"mutation {{ {nest_mutation(path, value)} }}"
        with assertable_controller.assert_write_here(["write_bool"]):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, value)

    def test_string_enum(self, assertable_controller, client):
        expect = ""
        path = ["stringEnum"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["string_enum"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

        new = "new"
        mutation = f"mutation {{ {nest_mutation(path, new)} }}"
        with assertable_controller.assert_write_here(["string_enum"]):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, new)

    def test_big_enum(self, assertable_controller, client):
        expect = 0
        path = ["bigEnum"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["big_enum"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_go(self, assertable_controller, client):
        path = ["go"]
        mutation = f"mutation {{ {nest_query(path)} }}"
        with assertable_controller.assert_execute_here(path):
            response = client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200
        assert response.json()["data"] == {path[-1]: True}

    def test_read_child1(self, assertable_controller, client):
        expect = 0
        path = ["SubController01", "readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["SubController01", "read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)

    def test_read_child2(self, assertable_controller, client):
        expect = 0
        path = ["SubController02", "readInt"]
        query = f"query {{ {nest_query(path)} }}"
        with assertable_controller.assert_read_here(["SubController02", "read_int"]):
            response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        assert response.json()["data"] == nest_responce(path, expect)
