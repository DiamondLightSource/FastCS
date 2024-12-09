import time
from collections.abc import Callable

from p4p.nt import NTEnum, NTNDArray, NTScalar

from fastcs.attributes import AttrR, AttrW
from fastcs.datatypes import (
    Bool,
    DataType,
    Enum,
    Float,
    Int,
    String,
    T,
    WaveForm,
)
from fastcs.exceptions import FastCSException

P4P_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String, WaveForm)


def pv_metadata_from_datatype(datatype: DataType) -> dict:
    initial_value = datatype.initial_value
    match datatype:
        case Bool():
            nt = NTScalar("b")
        case Int():
            nt = NTScalar("i")
        case Float():
            nt = NTScalar("d")
        case Float():
            nt = NTScalar("s")
        case Enum():
            initial_value = datatype.index_of(datatype.initial_value)
            nt = NTEnum(choices=[member.name for member in datatype.members])
        case WaveForm():
            nt = NTNDArray()
        case _:
            raise FastCSException(f"Unsupported datatype {datatype}")

    return {"nt": nt, "initial": initial_value}


def get_callable_from_epics_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case Enum():

            def cast_from_epics_type(value: object) -> T:
                return datatype.validate(datatype.members[value])

        case datatype if issubclass(type(datatype), P4P_ALLOWED_DATATYPES):

            def cast_from_epics_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_from_epics_type


def get_callable_to_epics_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case Enum():

            def cast_to_epics_type(value) -> object:
                return datatype.index_of(datatype.validate(value))
        case datatype if issubclass(type(datatype), P4P_ALLOWED_DATATYPES):

            def cast_to_epics_type(value) -> object:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_to_epics_type


class AttrRHandler:
    def __init__(self, attribute: AttrR[T]):
        super().__init__()
        self._attribute = attribute
        self._cast_to_epics_type = get_callable_to_epics_type(attribute.datatype)

        """
        async def update_record_from_attribute(value: T):
            self._pv.post(self._cast_to_epics_type(value))

        attribute.set_update_callback(update_record_from_attribute)
        """

    async def rpc(self, pv, op):
        print("RPC")
        pv.close()
        pv.open(1)


class AttrWHandler:
    def __init__(self, attribute: AttrW[T]):
        super().__init__()
        self._attribute = attribute
        self._cast_from_epics_type = get_callable_from_epics_type(attribute.datatype)

    async def put(self, pv, op):
        raw_value = op.value()
        print("USING PUT", raw_value)
        # self._attribute.process(self._cast_from_epics_type(raw_value))

        pv.post(raw_value, timestamp=time.time())
        op.done()


class AttrRWHandler(AttrRHandler, AttrWHandler):
    pass
