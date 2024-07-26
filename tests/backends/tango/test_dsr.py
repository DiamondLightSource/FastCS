import pytest
from pytest_mock import MockerFixture
from tango._tango import AttrWriteType, CmdArgType

from fastcs.backends.tango.dsr import _collect_dev_attributes, _collect_dev_commands


def test_collect_attributes(mapping):
    attributes = _collect_dev_attributes(mapping)

    # Check that attributes are created and of expected type
    assert list(attributes.keys()) == [
        "ReadInt",
        "ReadWriteFloat",
        "StringEnum",
        "WriteBool",
    ]
    assert attributes["ReadInt"].attr_write == AttrWriteType.READ
    assert attributes["ReadInt"].attr_type == CmdArgType.DevLong64
    assert attributes["StringEnum"].attr_write == AttrWriteType.READ_WRITE
    assert attributes["StringEnum"].attr_type == CmdArgType.DevString
    assert attributes["ReadWriteFloat"].attr_write == AttrWriteType.READ_WRITE
    assert attributes["ReadWriteFloat"].attr_type == CmdArgType.DevDouble
    assert attributes["WriteBool"].attr_write == AttrWriteType.WRITE
    assert attributes["WriteBool"].attr_type == CmdArgType.DevBoolean


@pytest.mark.asyncio
async def test_collect_commands(mapping, mocker: MockerFixture):
    commands = _collect_dev_commands(mapping)

    # Check that command is created and it can be called
    assert list(commands.keys()) == ["Go"]
    await commands["Go"](mocker.MagicMock())
