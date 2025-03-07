import pytest

from fastcs.attributes import AttrR
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Int


def test_controller_nesting():
    controller = Controller()
    sub_controller = SubController()
    sub_sub_controller = SubController()

    controller.register_sub_controller("a", sub_controller)
    sub_controller.register_sub_controller("b", sub_sub_controller)

    assert sub_controller.path == ["a"]
    assert sub_sub_controller.path == ["a", "b"]
    assert controller.get_sub_controllers() == {"a": sub_controller}
    assert sub_controller.get_sub_controllers() == {"b": sub_sub_controller}

    with pytest.raises(
        ValueError, match=r"Controller .* already has a SubController registered as .*"
    ):
        controller.register_sub_controller("a", SubController())

    with pytest.raises(
        ValueError, match=r"SubController is already registered under .*"
    ):
        controller.register_sub_controller("c", sub_controller)


class SomeSubController(SubController):
    def __init__(self):
        super().__init__()

    sub_attribute = AttrR(Int())

    root_attribute = AttrR(Int())


class SomeController(Controller):
    annotated_attr: AttrR
    annotated_attr_not_defined_in_init: AttrR[int]
    equal_attr = AttrR(Int())
    annotated_and_equal_attr: AttrR[int] = AttrR(Int())

    def __init__(self, sub_controller: SubController):
        self.attributes = {}

        self.annotated_attr = AttrR(Int())
        self.attr_on_object = AttrR(Int())

        self.attributes["_attributes_attr"] = AttrR(Int())
        self.attributes["_attributes_attr_equal"] = self.equal_attr

        super().__init__()
        self.register_sub_controller("sub_controller", sub_controller)


def test_attribute_parsing():
    sub_controller = SomeSubController()
    controller = SomeController(sub_controller)

    assert set(controller.attributes.keys()) == {
        "_attributes_attr",
        "annotated_attr",
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


def test_attribute_in_both_class_and_get_attributes():
    class FailingController(Controller):
        duplicate_attribute = AttrR(Int())

        def __init__(self):
            self.attributes = {"duplicate_attribute": AttrR(Int())}
            super().__init__()

    with pytest.raises(
        ValueError,
        match=(
            "`FailingController` has conflicting attribute `duplicate_attribute` "
            "already present in the attributes dict."
        ),
    ):
        FailingController()


def test_root_attribute():
    class FailingController(SomeController):
        sub_controller = AttrR(Int())

    with pytest.raises(
        TypeError,
        match=(
            "Cannot set SubController `sub_controller` root attribute "
            "on the parent controller `FailingController` as it already "
            "has an attribute of that name."
        ),
    ):
        FailingController(SomeSubController())
