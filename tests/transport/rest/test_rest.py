import enum

import numpy as np
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
from fastcs.datatypes import Bool, Enum, Float, Int, String, WaveForm
from fastcs.transport.rest.adapter import RestTransport


class RestAssertableController(AssertableController):
    read_int = AttrR(Int(), handler=TestUpdater())
    read_write_int = AttrRW(Int(), handler=TestHandler())
    read_write_float = AttrRW(Float())
    read_bool = AttrR(Bool())
    write_bool = AttrW(Bool(), handler=TestSender())
    read_string = AttrRW(String())
    enum = AttrRW(Enum(enum.IntEnum("Enum", {"RED": 0, "GREEN": 1, "BLUE": 2})))
    one_d_waveform = AttrRW(WaveForm(np.int32, (10,)))
    two_d_waveform = AttrRW(WaveForm(np.int32, (10, 10)))


@pytest.fixture(scope="class")
def assertable_controller(class_mocker: MockerFixture):
    return RestAssertableController(class_mocker)


class TestRestServer:
    @pytest.fixture(scope="class")
    def client(self, assertable_controller):
        app = RestTransport(assertable_controller)._server._app
        with TestClient(app) as client:
            yield client

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

    def test_read_int(self, assertable_controller, client):
        expect = 0
        with assertable_controller.assert_read_here(["read_int"]):
            response = client.get("/read-int")
        assert response.status_code == 200
        assert response.json()["value"] == expect

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

    def test_enum(self, assertable_controller, client):
        enum_attr = assertable_controller.attributes["enum"]
        enum_cls = enum_attr.datatype.dtype
        assert isinstance(enum_attr.get(), enum_cls)
        assert enum_attr.get() == enum_cls(0)
        expect = 0
        with assertable_controller.assert_read_here(["enum"]):
            response = client.get("/enum")
        assert response.status_code == 200
        assert response.json()["value"] == expect
        new = 2
        with assertable_controller.assert_write_here(["enum"]):
            response = client.put("/enum", json={"value": new})
        assert client.get("/enum").json()["value"] == new
        assert isinstance(enum_attr.get(), enum_cls)
        assert enum_attr.get() == enum_cls(2)

    def test_1d_waveform(self, assertable_controller, client):
        attribute = assertable_controller.attributes["one_d_waveform"]
        expect = np.zeros((10,), dtype=np.int32)
        assert np.array_equal(attribute.get(), expect)
        assert isinstance(attribute.get(), np.ndarray)

        with assertable_controller.assert_read_here(["one_d_waveform"]):
            response = client.get("one-d-waveform")
        assert np.array_equal(response.json()["value"], expect)
        new = [1, 2, 3]
        with assertable_controller.assert_write_here(["one_d_waveform"]):
            client.put("/one-d-waveform", json={"value": new})
        assert np.array_equal(client.get("/one-d-waveform").json()["value"], new)

        result = client.get("/one-d-waveform")
        assert np.array_equal(result.json()["value"], new)
        assert np.array_equal(attribute.get(), new)
        assert isinstance(attribute.get(), np.ndarray)

    def test_2d_waveform(self, assertable_controller, client):
        attribute = assertable_controller.attributes["two_d_waveform"]
        expect = np.zeros((10, 10), dtype=np.int32)
        assert np.array_equal(attribute.get(), expect)
        assert isinstance(attribute.get(), np.ndarray)

        with assertable_controller.assert_read_here(["two_d_waveform"]):
            result = client.get("/two-d-waveform")
        assert np.array_equal(result.json()["value"], expect)
        new = [[1, 2, 3], [4, 5, 6]]
        with assertable_controller.assert_write_here(["two_d_waveform"]):
            client.put("/two-d-waveform", json={"value": new})

        result = client.get("/two-d-waveform")
        assert np.array_equal(result.json()["value"], new)
        assert np.array_equal(attribute.get(), new)
        assert isinstance(attribute.get(), np.ndarray)

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
