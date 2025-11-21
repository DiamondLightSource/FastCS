import numpy as np

from fastcs.datatypes.bool import Bool
from fastcs.datatypes.datatype import DataType
from fastcs.datatypes.float import Float
from fastcs.datatypes.int import Int
from fastcs.datatypes.string import String


def numpy_to_fastcs_datatype(np_type) -> DataType:
    """Converts numpy types to fastcs types for widget creation.
    Only types important for widget creation are explicitly converted
    """
    if np.issubdtype(np_type, np.integer):
        return Int()
    elif np.issubdtype(np_type, np.floating):
        return Float()
    elif np.issubdtype(np_type, np.bool_):
        return Bool()
    else:
        return String()
