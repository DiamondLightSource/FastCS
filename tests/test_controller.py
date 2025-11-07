import pytest

from fastcs.attributes import AttrR
from fastcs.controller import Controller, ControllerVector
from fastcs.datatypes import Float, Int


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

    with pytest.raises(ValueError, match=r"existing sub controller"):
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


def test_conflicting_attributes_and_controllers():
    class ConflictingController(Controller):
        attr = AttrR(Int())

        def __init__(self):
            super().__init__()
            self.sub_controller = Controller()

    controller = ConflictingController()

    with pytest.raises(ValueError, match=r"Cannot add attribute .* existing attribute"):
        controller.attr = AttrR(Float())  # pyright: ignore[reportAttributeAccessIssue]

    with pytest.raises(
        ValueError, match=r"Cannot add sub controller .* existing attribute"
    ):
        controller.attr = Controller()  # pyright: ignore[reportAttributeAccessIssue]

    with pytest.raises(
        ValueError, match=r"Cannot add sub controller .* existing sub controller"
    ):
        controller.sub_controller = Controller()

    with pytest.raises(
        ValueError, match=r"Cannot add attribute .* existing sub controller"
    ):
        controller.sub_controller = AttrR(Int())  # pyright: ignore[reportAttributeAccessIssue]


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
