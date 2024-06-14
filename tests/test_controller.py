from fastcs.controller import Controller, SubController
from fastcs.mapping import _get_single_mapping, _walk_mappings


def test_controller_nesting():
    controller = Controller()
    sub_controller = SubController(["a"])
    sub_sub_controller = SubController(["a", "b"])

    controller.register_sub_controller(sub_controller)
    sub_controller.register_sub_controller(sub_sub_controller)

    assert list(_walk_mappings(controller)) == [
        _get_single_mapping(controller),
        _get_single_mapping(sub_controller),
        _get_single_mapping(sub_sub_controller),
    ]
