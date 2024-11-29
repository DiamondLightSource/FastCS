import pytest
from fastapi.testclient import TestClient

from fastcs.transport.rest.adapter import RestTransport


class TestRestServer:
    @pytest.fixture(scope="class")
    def client(self, assertable_controller):
        app = RestTransport(assertable_controller)._server._app
        with TestClient(app) as client:
            yield client

    def test_read_int(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["read_int"]):
            response = client.get("/read-int")
        assert response.status_code == 200
        assert response.json()["value"] == expect

    def test_read_write_int(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["read_write_int"]):
            response = client.get("/read-write-int")
        assert response.status_code == 200
        assert response.json()["value"] == expect
        new = 9
        with assertable_controller.assert_write_here(["read_write_int"]):
            response = client.put("/read-write-int", json={"value": new})
        assert client.get("/read-write-int").json()["value"] == new

    def test_read_write_float(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["read_write_float"]):
            response = client.get("/read-write-float")
        assert response.status_code == 200
        assert response.json()["value"] == expect
        new = 0.5
        with assertable_controller.assert_write_here(["read_write_float"]):
            response = client.put("/read-write-float", json={"value": new})
        assert client.get("/read-write-float").json()["value"] == new

    def test_read_bool(self, assertable_controller, client):
        expect = False
        with assertable_controller.assert_read_here(["read_bool"]):
            response = client.get("/read-bool")
        assert response.status_code == 200
        assert response.json()["value"] == expect

    def test_write_bool(self, assertable_controller, client):
        with assertable_controller.assert_write_here(["write_bool"]):
            client.put("/write-bool", json={"value": True})

    def test_string_enum(self, assertable_controller, client):
        expect = ""
        with assertable_controller.assert_read_here(["string_enum"]):
            response = client.get("/string-enum")
        assert response.status_code == 200
        assert response.json()["value"] == expect
        new = "new"
        with assertable_controller.assert_write_here(["string_enum"]):
            response = client.put("/string-enum", json={"value": new})
        assert client.get("/string-enum").json()["value"] == new

    def test_big_enum(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["big_enum"]):
            response = client.get("/big-enum")
        assert response.status_code == 200
        assert response.json()["value"] == expect

    def test_go(self, assertable_controller, client):
        with assertable_controller.assert_execute_here(["go"]):
            response = client.put("/go")
            assert response.status_code == 204

    def test_read_child1(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["SubController01", "read_int"]):
            response = client.get("/SubController01/read-int")
        assert response.status_code == 200
        assert response.json()["value"] == expect

    def test_read_child2(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["SubController02", "read_int"]):
            response = client.get("/SubController02/read-int")
        assert response.status_code == 200
        assert response.json()["value"] == expect
