from enum import IntEnum

import numpy as np
import pytest

from fastcs.datatypes import DataType, Enum, Float, Int, Waveform


def test_base_validate():
    class TestInt(DataType[int]):
        @property
        def dtype(self) -> type[int]:
            return int

    class MyIntEnum(IntEnum):
        A = 0
        B = 1

    test_int = TestInt()

    assert test_int.validate("0") == 0
    assert test_int.validate(MyIntEnum.B) == 1

    with pytest.raises(ValueError, match="Failed to cast"):
        test_int.validate("foo")


@pytest.mark.parametrize(
    ["datatype", "init_args", "value"],
    [
        (Int, {"min": 1}, 0),
        (Int, {"max": -1}, 0),
        (Float, {"min": 1}, 0.0),
        (Float, {"max": -1}, 0.0),
        (Enum, {"enum_cls": int}, 0),
        (Waveform, {"array_dtype": "U64", "shape": (1,)}, np.ndarray([1])),
        (Waveform, {"array_dtype": "float64", "shape": (1, 1)}, np.ndarray([1])),
    ],
)
def test_validate(datatype, init_args, value):
    with pytest.raises(ValueError):
        datatype(**init_args).validate(value)
