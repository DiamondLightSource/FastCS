import asyncio
import enum
from datetime import datetime
from multiprocessing import Queue
from unittest.mock import ANY
from uuid import uuid4

import numpy as np
import pytest
from numpy.typing import DTypeLike
from p4p import Value
from p4p.client.asyncio import Context
from p4p.client.thread import Context as ThreadContext
from p4p.nt import NTTable

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Enum, Float, Int, String, Table, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.transport.epics.pva.options import EpicsPVAOptions
from fastcs.wrappers import command


@pytest.mark.asyncio
async def test_ioc(p4p_subprocess: tuple[str, Queue]):
    pv_prefix, _ = p4p_subprocess
    ctxt = Context("pva")

    _parent_pvi = await ctxt.get(f"{pv_prefix}:PVI")
    assert isinstance(_parent_pvi, Value)
    parent_pvi = _parent_pvi.todict()
    assert all(f in parent_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert parent_pvi["display"] == {"description": "some controller"}
    assert parent_pvi["value"] == {
        "a": {"rw": f"{pv_prefix}:A"},
        "b": {"w": f"{pv_prefix}:B"},
        "child": {
            "d": {
                "v1": f"{pv_prefix}:Child1:PVI",
                "v2": f"{pv_prefix}:Child2:PVI",
            }
        },
        "table": {
            "rw": f"{pv_prefix}:Table",
        },
    }

    child_pvi_pv = parent_pvi["value"]["child"]["d"]["v1"]
    _child_pvi = await ctxt.get(child_pvi_pv)
    assert isinstance(_child_pvi, Value)
    child_pvi = _child_pvi.todict()
    assert all(f in child_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert child_pvi["display"] == {"description": "some sub controller"}
    assert child_pvi["value"] == {
        "c": {"w": f"{pv_prefix}:Child1:C"},
        "d": {"x": f"{pv_prefix}:Child1:D"},
        "e": {"r": f"{pv_prefix}:Child1:E"},
        "f": {"rw": f"{pv_prefix}:Child1:F"},
        "g": {"rw": f"{pv_prefix}:Child1:G"},
        "h": {"rw": f"{pv_prefix}:Child1:H"},
        "i": {"x": f"{pv_prefix}:Child1:I"},
        "j": {"r": f"{pv_prefix}:Child1:J"},
    }


@pytest.mark.asyncio
async def test_scan_method(p4p_subprocess: tuple[str, Queue]):
    pv_prefix, _ = p4p_subprocess
    ctxt = Context("pva")
    e_values = asyncio.Queue()

    # While the scan method will update every 0.1 seconds, it takes around that
    # time for the p4p backends to update, broadcast, get.
    LATENCY = 1e8

    e_monitor = ctxt.monitor(f"{pv_prefix}:Child1:E", e_values.put)
    try:
        # Throw away the value on the ioc setup so we can compare timestamps
        _ = await e_values.get()

        raw_value = (await e_values.get()).raw
        value = raw_value["value"]
        assert isinstance(value, bool)
        nanoseconds = raw_value["timeStamp"]["nanoseconds"]

        new_raw_value = (await e_values.get()).raw
        assert new_raw_value["value"] is not value
        assert new_raw_value["timeStamp"]["nanoseconds"] == pytest.approx(
            nanoseconds + 1e8, abs=LATENCY
        )
        value = new_raw_value["value"]
        assert isinstance(value, bool)
        nanoseconds = new_raw_value["timeStamp"]["nanoseconds"]

        new_raw_value = (await e_values.get()).raw
        assert new_raw_value["value"] is not value
        assert new_raw_value["timeStamp"]["nanoseconds"] == pytest.approx(
            nanoseconds + 1e8, abs=LATENCY
        )

    finally:
        e_monitor.close()


@pytest.mark.asyncio
async def test_command_method(p4p_subprocess: tuple[str, Queue]):
    pv_prefix, _ = p4p_subprocess
    d_values = asyncio.Queue()
    i_values = asyncio.Queue()
    j_values = asyncio.Queue()
    ctxt = Context("pva")

    d_monitor = ctxt.monitor(f"{pv_prefix}:Child1:D", d_values.put)
    i_monitor = ctxt.monitor(f"{pv_prefix}:Child1:I", i_values.put)
    j_monitor = ctxt.monitor(f"{pv_prefix}:Child1:J", j_values.put)

    try:
        j_initial_value = await j_values.get()
        assert (await d_values.get()).raw.value is False
        await ctxt.put(f"{pv_prefix}:Child1:D", True)
        assert (await d_values.get()).raw.value is True
        # D process hangs for 0.1s, so we wait slightly longer
        await asyncio.sleep(0.2)
        # Value returns to False, signifying completed process
        assert (await d_values.get()).raw.value is False
        # D process increments J by 1
        assert (await j_values.get()).raw.value == j_initial_value + 1

        # First run fails
        before_command_value = (await i_values.get()).raw
        assert before_command_value["value"] is False
        assert before_command_value["alarm"]["severity"] == 0
        assert before_command_value["alarm"]["message"] == ""
        await ctxt.put(f"{pv_prefix}:Child1:I", True)
        assert (await i_values.get()).raw.value is True
        await asyncio.sleep(0.2)

        after_command_value = (await i_values.get()).raw
        assert after_command_value["value"] is False
        assert after_command_value["alarm"]["severity"] == 2
        assert (
            after_command_value["alarm"]["message"] == "I: FAILED WITH THIS WEIRD ERROR"
        )
        # Failed I process does not increment J
        assert j_values.empty()

        # Second run succeeds
        await ctxt.put(f"{pv_prefix}:Child1:I", True)
        assert (await i_values.get()).raw.value is True
        await asyncio.sleep(0.2)
        after_command_value = (await i_values.get()).raw
        # Successful I process increments J by 1
        assert (await j_values.get()).raw.value == j_initial_value + 2

        # On the second run the command succeeded so we left the error state
        assert after_command_value["value"] is False
        assert after_command_value["alarm"]["severity"] == 0
        assert after_command_value["alarm"]["message"] == ""

    finally:
        d_monitor.close()
        i_monitor.close()
        j_monitor.close()


@pytest.mark.asyncio
async def test_numerical_alarms(p4p_subprocess: tuple[str, Queue]):
    pv_prefix, _ = p4p_subprocess
    a_values = asyncio.Queue()
    b_values = asyncio.Queue()
    ctxt = Context("pva")

    a_monitor = ctxt.monitor(f"{pv_prefix}:A", a_values.put)
    b_monitor = ctxt.monitor(f"{pv_prefix}:B", b_values.put)

    try:
        value = (await a_values.get()).raw
        assert value["value"] == 0
        assert isinstance(value["value"], int)
        assert value["alarm"]["severity"] == 0
        assert value["alarm"]["message"] == "No alarm"

        value = (await b_values.get()).raw
        assert value["value"] == 0
        assert isinstance(value["value"], float)
        assert value["alarm"]["severity"] == 0
        assert value["alarm"]["message"] == "No alarm"

        await ctxt.put(f"{pv_prefix}:A", 40_001)
        await ctxt.put(f"{pv_prefix}:B", -0.6)

        value = (await a_values.get()).raw
        assert value["value"] == 40_001
        assert isinstance(value["value"], int)
        assert value["alarm"]["severity"] == 2
        assert value["alarm"]["message"] == "Above maximum alarm limit: 40000"

        value = (await b_values.get()).raw
        assert value["value"] == -0.6
        assert isinstance(value["value"], float)
        assert value["alarm"]["severity"] == 2
        assert value["alarm"]["message"] == "Below minimum alarm limit: -0.5"

        await ctxt.put(f"{pv_prefix}:A", 40_000)
        await ctxt.put(f"{pv_prefix}:B", -0.5)

        value = (await a_values.get()).raw
        assert value["value"] == 40_000
        assert isinstance(value["value"], int)
        assert value["alarm"]["severity"] == 0
        assert value["alarm"]["message"] == "No alarm"

        value = (await b_values.get()).raw
        assert value["value"] == -0.5
        assert isinstance(value["value"], float)
        assert value["alarm"]["severity"] == 0
        assert value["alarm"]["message"] == "No alarm"

        assert a_values.empty()
        assert b_values.empty()

    finally:
        a_monitor.close()
        b_monitor.close()


def make_fastcs(pv_prefix: str, controller: Controller) -> FastCS:
    epics_options = EpicsPVAOptions(pva_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))
    return FastCS(controller, [epics_options])


def test_read_signal_set():
    class SomeController(Controller):
        a: AttrRW = AttrRW(Int(max=400_000, max_alarm=40_000))
        b: AttrR = AttrR(Float(min=-1, min_alarm=-0.5, prec=2))

    controller = SomeController()
    pv_prefix = str(uuid4())
    fastcs = make_fastcs(pv_prefix, controller)

    ctxt = ThreadContext("pva")

    async def _wait_and_set_attr_r():
        await asyncio.sleep(0.05)
        await controller.a.set(40_000)
        await controller.b.set(-0.99)
        await asyncio.sleep(0.05)
        await controller.a.set(-100)
        await controller.b.set(-0.99)
        await controller.b.set(-0.9111111)

    a_values, b_values = [], []
    a_monitor = ctxt.monitor(f"{pv_prefix}:A_RBV", a_values.append)
    b_monitor = ctxt.monitor(f"{pv_prefix}:B", b_values.append)
    serve = asyncio.ensure_future(fastcs.serve())
    wait_and_set_attr_r = asyncio.ensure_future(_wait_and_set_attr_r())
    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(asyncio.gather(serve, wait_and_set_attr_r), timeout=0.2)
        )
    except TimeoutError:
        ...
    finally:
        a_monitor.close()
        b_monitor.close()
        serve.cancel()
        wait_and_set_attr_r.cancel()
        assert a_values == [0, 40_000, -100]
        assert b_values == [0.0, -0.99, -0.99, -0.91]  # Last is -0.91 because of prec


def test_pvi_grouping():
    class ChildChildController(SubController):
        attr_e: AttrRW = AttrRW(Int())
        attr_f: AttrR = AttrR(String())

    class ChildController(SubController):
        attr_c: AttrW = AttrW(Bool(), description="Some bool")
        attr_d: AttrW = AttrW(String())

    class SomeController(Controller):
        description = "some controller"
        attr_1: AttrRW = AttrRW(Int(max=400_000, max_alarm=40_000))
        attr_1: AttrRW = AttrRW(Float(min=-1, min_alarm=-0.5, prec=2))
        another_attr_0: AttrRW = AttrRW(Int())
        another_attr_1000: AttrRW = AttrRW(Int())
        a_third_attr: AttrW = AttrW(Int())
        child_attribute_same_name: AttrR = AttrR(Int())

    controller = SomeController()

    sub_controller = ChildController()
    controller.register_sub_controller("Child0", sub_controller)
    sub_controller.register_sub_controller("ChildChild", ChildChildController())
    sub_controller = ChildController()
    controller.register_sub_controller("Child1", sub_controller)
    sub_controller.register_sub_controller("ChildChild", ChildChildController())
    sub_controller = ChildController()
    controller.register_sub_controller("Child2", sub_controller)
    sub_controller.register_sub_controller("ChildChild", ChildChildController())
    sub_controller = ChildController()
    controller.register_sub_controller("another_child", sub_controller)
    sub_controller.register_sub_controller("ChildChild", ChildChildController())
    sub_controller = ChildController()
    controller.register_sub_controller("AdditionalChild", sub_controller)
    sub_controller.register_sub_controller("ChildChild", ChildChildController())
    sub_controller = ChildController()
    controller.register_sub_controller("child_attribute_same_name", sub_controller)

    pv_prefix = str(uuid4())
    fastcs = make_fastcs(pv_prefix, controller)

    ctxt = ThreadContext("pva")

    controller_pvi, child_controller_pvi, child_child_controller_pvi = [], [], []
    controller_monitor = ctxt.monitor(f"{pv_prefix}:PVI", controller_pvi.append)
    child_controller_monitor = ctxt.monitor(
        f"{pv_prefix}:Child0:PVI", child_controller_pvi.append
    )
    child_child_controller_monitor = ctxt.monitor(
        f"{pv_prefix}:Child0:ChildChild:PVI", child_child_controller_pvi.append
    )
    serve = asyncio.ensure_future(fastcs.serve())

    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(serve, timeout=0.2)
        )
    except TimeoutError:
        ...
    finally:
        controller_monitor.close()
        child_controller_monitor.close()
        child_child_controller_monitor.close()
        serve.cancel()

        assert len(controller_pvi) == 1
        assert controller_pvi[0].todict() == {
            "alarm": {"message": "", "severity": 0, "status": 0},
            "display": {"description": "some controller"},
            "timeStamp": {
                "nanoseconds": ANY,
                "secondsPastEpoch": ANY,
                "userTag": 0,
            },
            "value": {
                "additional_child": {"d": f"{pv_prefix}:AdditionalChild:PVI"},
                "another_child": {"d": f"{pv_prefix}:AnotherChild:PVI"},
                "another_attr0": {"rw": f"{pv_prefix}:AnotherAttr0"},
                "another_attr1000": {"rw": f"{pv_prefix}:AnotherAttr1000"},
                "a_third_attr": {"w": f"{pv_prefix}:AThirdAttr"},
                "attr1": {"rw": f"{pv_prefix}:Attr1"},
                "child": {
                    "d": {
                        "v0": f"{pv_prefix}:Child0:PVI",
                        "v1": f"{pv_prefix}:Child1:PVI",
                        "v2": f"{pv_prefix}:Child2:PVI",
                    }
                },
                "child_attribute_same_name": {
                    "d": f"{pv_prefix}:ChildAttributeSameName:PVI",
                    "r": f"{pv_prefix}:ChildAttributeSameName",
                },
            },
        }
        assert len(child_controller_pvi) == 1
        assert child_controller_pvi[0].todict() == {
            "alarm": {"message": "", "severity": 0, "status": 0},
            "display": {"description": ""},
            "timeStamp": {
                "nanoseconds": ANY,
                "secondsPastEpoch": ANY,
                "userTag": 0,
            },
            "value": {
                "attr_c": {"w": f"{pv_prefix}:Child0:AttrC"},
                "attr_d": {
                    "w": f"{pv_prefix}:Child0:AttrD",
                },
                "child_child": {"d": f"{pv_prefix}:Child0:ChildChild:PVI"},
            },
        }
        assert len(child_child_controller_pvi) == 1
        assert child_child_controller_pvi[0].todict() == {
            "alarm": {"message": "", "severity": 0, "status": 0},
            "display": {"description": ""},
            "timeStamp": {
                "nanoseconds": ANY,
                "secondsPastEpoch": ANY,
                "userTag": 0,
            },
            "value": {
                "attr_e": {"rw": f"{pv_prefix}:Child0:ChildChild:AttrE"},
                "attr_f": {"r": f"{pv_prefix}:Child0:ChildChild:AttrF"},
            },
        }


def test_more_exotic_dataypes():
    table_columns: list[tuple[str, DTypeLike]] = [
        ("A", "i"),
        ("B", "i"),
        ("C", "?"),
        ("D", "f"),
        ("E", "h"),
    ]

    class AnEnum(enum.Enum):
        A = 1
        B = 0
        C = 3

    class SomeController(Controller):
        some_waveform: AttrRW = AttrRW(Waveform(np.int64, shape=(10, 10)))
        some_table: AttrRW = AttrRW(Table(table_columns))
        some_enum: AttrRW = AttrRW(Enum(AnEnum))

    controller = SomeController()
    pv_prefix = str(uuid4())
    fastcs = make_fastcs(pv_prefix, controller)

    ctxt = ThreadContext("pva", nt=False)

    initial_waveform_value = np.zeros((10, 10), dtype=np.int64)
    initial_table_value = np.array([], dtype=table_columns)
    initial_enum_value = AnEnum.A

    server_set_waveform_value = np.copy(initial_waveform_value)
    server_set_waveform_value[0] = np.arange(10)
    server_set_table_value = np.array([(1, 2, False, 3.14, 1)], dtype=table_columns)
    server_set_enum_value = AnEnum.B

    client_put_waveform_value = np.copy(server_set_waveform_value)
    client_put_waveform_value[1] = np.arange(10)
    client_put_table_value = NTTable(columns=table_columns).wrap(
        [
            {"A": 1, "B": 2, "C": False, "D": 3.14, "E": 1},
            {"A": 5, "B": 2, "C": True, "D": 6.28, "E": 2},
        ]
    )
    client_put_enum_value = "C"

    async def _wait_and_set_attrs():
        await asyncio.sleep(0.1)
        # This demonstrates an update from hardware,
        # resulting in only a change in the read back.
        await asyncio.gather(
            controller.some_waveform.set(server_set_waveform_value),
            controller.some_table.set(server_set_table_value),
            controller.some_enum.set(server_set_enum_value),
        )

    async def _wait_and_put_pvs():
        await asyncio.sleep(0.3)
        ctxt = Context("pva")
        # This demonstrates a client put,
        # resulting in a change in the demand and read back.
        await asyncio.gather(
            ctxt.put(f"{pv_prefix}:SomeWaveform", client_put_waveform_value),
            ctxt.put(f"{pv_prefix}:SomeTable", client_put_table_value),
            ctxt.put(f"{pv_prefix}:SomeEnum", client_put_enum_value),
        )

    waveform_values, table_values, enum_values = [], [], []

    # Monitoring read backs to capture both client and server sets.
    waveform_monitor = ctxt.monitor(
        f"{pv_prefix}:SomeWaveform_RBV", waveform_values.append
    )
    table_monitor = ctxt.monitor(f"{pv_prefix}:SomeTable_RBV", table_values.append)
    enum_monitor = ctxt.monitor(
        f"{pv_prefix}:SomeEnum_RBV",
        enum_values.append,
    )

    serve = asyncio.ensure_future(fastcs.serve())
    wait_and_set_attrs = asyncio.ensure_future(_wait_and_set_attrs())
    wait_and_put_pvs = asyncio.ensure_future(_wait_and_put_pvs())
    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(
                asyncio.gather(serve, wait_and_set_attrs, wait_and_put_pvs),
                timeout=0.6,
            )
        )
    except TimeoutError:
        ...
    finally:
        waveform_monitor.close()
        table_monitor.close()
        enum_monitor.close()
        serve.cancel()
        wait_and_set_attrs.cancel()
        wait_and_put_pvs.cancel()

        expected_waveform_gets = [
            initial_waveform_value,
            server_set_waveform_value,
            client_put_waveform_value,
        ]

        for expected_waveform, actual_waveform in zip(
            expected_waveform_gets, waveform_values, strict=True
        ):
            np.testing.assert_array_equal(
                expected_waveform, actual_waveform.todict()["value"].reshape(10, 10)
            )

        expected_table_gets = [
            NTTable(columns=table_columns).wrap(initial_table_value),
            NTTable(columns=table_columns).wrap(server_set_table_value),
            client_put_table_value,
        ]
        for expected_table, actual_table in zip(
            expected_table_gets, table_values, strict=True
        ):
            expected_table = expected_table.todict()["value"]
            actual_table = actual_table.todict()["value"]
            for expected_column, actual_column in zip(
                expected_table.values(), actual_table.values(), strict=True
            ):
                if isinstance(expected_column, np.ndarray):
                    np.testing.assert_array_equal(expected_column, actual_column)
                else:
                    assert expected_column == actual_column and actual_column is None

        expected_enum_gets = [
            initial_enum_value,
            server_set_enum_value,
            AnEnum.C,
        ]

        for expected_enum, actual_enum in zip(
            expected_enum_gets, enum_values, strict=True
        ):
            assert (
                expected_enum
                == controller.some_enum.datatype.members[  # type: ignore
                    actual_enum.todict()["value"]["index"]
                ]
            )


def test_command_method_put_twice(caplog):
    class SomeController(Controller):
        command_runs_for_a_while_times = []
        command_spawns_a_task_times = []
        command_task_times = []

        @command()
        async def command_runs_for_a_while(self):
            start_time = datetime.now()
            await asyncio.sleep(0.1)
            self.command_runs_for_a_while_times.append((start_time, datetime.now()))

        @command()
        async def command_spawns_a_task(self):
            start_time = datetime.now()

            async def some_task():
                task_start_time = datetime.now()
                await asyncio.sleep(0.1)
                self.command_task_times.append((task_start_time, datetime.now()))

            self.command_spawns_a_task_times.append((start_time, datetime.now()))

            asyncio.create_task(some_task())

    controller = SomeController()
    pv_prefix = str(uuid4())
    fastcs = make_fastcs(pv_prefix, controller)
    expected_error_string = (
        "RuntimeError: Received request to run command but it is "
        "already in progress. Maybe the command should spawn an asyncio task?"
    )

    async def put_pvs():
        await asyncio.sleep(0.1)
        ctxt = Context("pva")
        await asyncio.gather(
            ctxt.put(f"{pv_prefix}:CommandSpawnsATask", True),
            ctxt.put(f"{pv_prefix}:CommandSpawnsATask", True),
        )
        assert expected_error_string not in caplog.text
        await asyncio.gather(
            ctxt.put(f"{pv_prefix}:CommandRunsForAWhile", True),
            ctxt.put(f"{pv_prefix}:CommandRunsForAWhile", True),
        )
        assert expected_error_string in caplog.text

    serve = asyncio.ensure_future(fastcs.serve())
    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(
                asyncio.gather(serve, put_pvs()),
                timeout=3,
            )
        )
    except TimeoutError:
        ...
    serve.cancel()

    assert (
        len(controller.command_task_times)
        == len(controller.command_spawns_a_task_times)
        == 2
    )
    for (task_start_time, task_end_time), (
        task_spawn_start_time,
        task_spawn_end_time,
    ) in zip(
        controller.command_task_times,
        controller.command_spawns_a_task_times,
        strict=True,
    ):
        assert (
            pytest.approx(
                (task_spawn_end_time - task_spawn_start_time).total_seconds(), abs=0.05
            )
            == 0
        )
        assert (
            pytest.approx((task_end_time - task_start_time).total_seconds(), abs=0.05)
            == 0.1
        )

    assert len(controller.command_runs_for_a_while_times) == 1
    coro_start_time, coro_end_time = controller.command_runs_for_a_while_times[0]
    assert (
        pytest.approx((coro_end_time - coro_start_time).total_seconds(), abs=0.05)
        == 0.1
    )


def test_block_flag_waits_for_callback_completion():
    class SomeController(Controller):
        @command()
        async def command_runs_for_a_while(self):
            await asyncio.sleep(0.2)

    controller = SomeController()
    pv_prefix = str(uuid4())
    fastcs = make_fastcs(pv_prefix, controller)
    command_runs_for_a_while_times = []

    async def put_pvs():
        ctxt = Context("pva")
        for block in [True, False]:
            start_time = datetime.now()
            await ctxt.put(
                f"{pv_prefix}:CommandRunsForAWhile",
                True,
                wait=block,
            )
            command_runs_for_a_while_times.append((start_time, datetime.now()))

    serve = asyncio.ensure_future(fastcs.serve())
    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(
                asyncio.gather(serve, put_pvs()),
                timeout=0.5,
            )
        )
    except TimeoutError:
        ...
    serve.cancel()

    assert len(command_runs_for_a_while_times) == 2

    for put_call, expected_duration in enumerate([0.2, 0]):
        start, end = command_runs_for_a_while_times[put_call]
        assert (
            pytest.approx((end - start).total_seconds(), abs=0.05) == expected_duration
        )
