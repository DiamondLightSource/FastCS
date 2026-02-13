import enum

import pytest

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller, ControllerVector
from fastcs.datatypes import Enum, Float, Int
from fastcs.methods import Command, Scan


def test_controller_nesting():
    controller = Controller()
    sub_controller = Controller()
    sub_sub_controller = Controller()

    controller.a = sub_controller
    sub_controller.b = sub_sub_controller

    assert sub_controller.path == ["a"]
    assert sub_sub_controller.path == ["a", "b"]
    assert controller.sub_controllers == {"a": sub_controller}
    assert sub_controller.sub_controllers == {"b": sub_sub_controller}

    with pytest.raises(ValueError, match=r"Cannot add sub controller"):
        controller.a = Controller()

    with pytest.raises(ValueError, match=r"already registered"):
        controller.c = sub_controller


class SomeSubController(Controller):
    def __init__(self):
        super().__init__()

    sub_attribute = AttrR(Int())

    root_attribute = AttrR(Int())


class SomeController(Controller):
    annotated_attr_not_defined_in_init: AttrR[int]
    equal_attr = AttrR(Int())
    annotated_and_equal_attr: AttrR[int] = AttrR(Int())

    def __init__(self, sub_controller: Controller):
        super().__init__()

        self.attr_on_object = AttrR(Int())

        self.attributes["_attributes_attr"] = AttrR(Int())
        self.attributes["_attributes_attr_equal"] = self.equal_attr

        self.sub_controller = sub_controller


def test_attribute_parsing():
    sub_controller = SomeSubController()
    controller = SomeController(sub_controller)

    assert set(controller.attributes.keys()) == {
        "_attributes_attr",
        "attr_on_object",
        "_attributes_attr_equal",
        "annotated_and_equal_attr",
        "equal_attr",
        "sub_controller",
    }

    assert SomeController.equal_attr is not controller.equal_attr
    assert (
        SomeController.annotated_and_equal_attr
        is not controller.annotated_and_equal_attr
    )

    assert sub_controller.attributes == {
        "sub_attribute": sub_controller.sub_attribute,
    }


async def noop() -> None:
    pass


@pytest.mark.parametrize(
    "member_name, member_value, expected_error",
    [
        ("attr", AttrR(Float()), r"Cannot add attribute"),
        ("attr", Controller(), r"Cannot add sub controller"),
        ("attr", Command(noop), r"Cannot add command"),
        ("sub_controller", AttrR(Int()), r"Cannot add attribute"),
        ("sub_controller", Controller(), r"Cannot add sub controller"),
        ("sub_controller", Command(noop), r"Cannot add command"),
        ("cmd", AttrR(Int()), r"Cannot add attribute"),
        ("cmd", Controller(), r"Cannot add sub controller"),
        ("cmd", Command(noop), r"Cannot add command"),
    ],
)
def test_conflicting_attributes_and_controllers_and_commands(
    member_name, member_value, expected_error
):
    class ConflictingController(Controller):
        attr = AttrR(Int())
        cmd = Command(noop)

        def __init__(self):
            super().__init__()
            self.sub_controller = Controller()

    controller = ConflictingController()

    with pytest.raises(ValueError, match=expected_error):
        setattr(controller, member_name, member_value)


def test_controller_raises_error_if_passed_numeric_sub_controller_name():
    sub_controller = SomeSubController()
    controller = SomeController(sub_controller)

    with pytest.raises(ValueError, match="Numeric-only names are not allowed"):
        controller.add_sub_controller("30", sub_controller)


def test_controller_vector_raises_error_if_add_sub_controller_called():
    controller_vector = ControllerVector({i: SomeSubController() for i in range(2)})

    with pytest.raises(NotImplementedError, match="Use __setitem__ instead"):
        controller_vector.add_sub_controller("subcontroller", SomeSubController())


def test_controller_vector_indexing():
    controller = SomeSubController()
    another_controller = SomeSubController()
    controller_vector = ControllerVector({1: another_controller})
    controller_vector[10] = controller
    assert controller_vector.sub_controllers["10"] == controller
    assert controller_vector[1] == another_controller
    assert len(controller_vector) == 2

    with pytest.raises(KeyError):
        _ = controller_vector[2]


def test_controller_vector_delitem_raises_exception():
    controller = SomeSubController()
    controller_vector = ControllerVector({1: controller})
    with pytest.raises(NotImplementedError, match="Cannot delete"):
        del controller_vector[1]


def test_controller_vector_iter():
    sub_controllers = {1: SomeSubController(), 2: SomeSubController()}
    controller_vector = ControllerVector(sub_controllers)

    for index, child in controller_vector.items():
        assert sub_controllers[index] == child


def test_attribute_hint_validation():
    class HintedController(Controller):
        read_write_int: AttrRW[int]

    controller = HintedController()

    with pytest.raises(RuntimeError, match="does not match defined datatype"):
        controller.add_attribute("read_write_int", AttrRW(Float()))

    with pytest.raises(RuntimeError, match="does not match defined access mode"):
        controller.add_attribute("read_write_int", AttrR(Int()))

    with pytest.raises(RuntimeError, match="failed to introspect hinted attribute"):
        controller.read_write_int = 5  # type: ignore
        controller._validate_type_hints()

    with pytest.raises(RuntimeError, match="failed to introspect hinted attribute"):
        controller._validate_type_hints()

    controller.add_attribute("read_write_int", AttrRW(Int()))


def test_enum_attribute_hint_validation():
    class GoodEnum(enum.IntEnum):
        VAL = 0

    class BadEnum(enum.IntEnum):
        VAL = 0

    class HintedController(Controller):
        enum: AttrRW[GoodEnum]

    controller = HintedController()

    with pytest.raises(RuntimeError, match="does not match defined datatype"):
        controller.add_attribute("enum", AttrRW(Enum(BadEnum)))

    controller.add_attribute("enum", AttrRW(Enum(GoodEnum)))


@pytest.mark.asyncio
async def test_sub_controller_hint_validation():
    class HintedController(Controller):
        child: SomeSubController

    controller = HintedController()

    with pytest.raises(RuntimeError, match="failed to introspect hinted controller"):
        controller._validate_type_hints()

    with pytest.raises(RuntimeError, match="does not match defined type"):
        controller.add_sub_controller("child", Controller())

    controller.add_sub_controller("child", SomeSubController())
    controller._validate_type_hints()


@pytest.mark.asyncio
async def test_method_hint_validation():
    class HintedController(Controller):
        method: Scan

    controller = HintedController()

    with pytest.raises(RuntimeError, match="failed to introspect hinted method"):
        controller._validate_type_hints()

    with pytest.raises(RuntimeError, match="Cannot add command method"):
        controller.add_command("method", Command(noop))

    controller.add_scan("method", Scan(fn=noop, period=0.1))

    controller._validate_type_hints()
