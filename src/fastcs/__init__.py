"""Top level API.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from . import attributes as attributes
from . import controller as controller
from . import cs_methods as cs_methods
from . import datatypes as datatypes
from . import transport as transport
from ._version import __version__ as __version__
from .launch import FastCS as FastCS
