from fastcs.controller import Controller, SubController
from fastcs.mapping import _get_single_mapping, _walk_mappings


def test_controller_nesting():
    controller = Controller()
    sub_controller = SubController()
    sub_sub_controller = SubController()

    controller.register_sub_controller("a", sub_controller)
    sub_controller.register_sub_controller("b", sub_sub_controller)

    assert sub_controller.path == ["a"]
    assert sub_sub_controller.path == ["a", "b"]
    assert list(_walk_mappings(controller)) == [
        _get_single_mapping(controller),
        _get_single_mapping(sub_controller),
        _get_single_mapping(sub_sub_controller),
    ]
