"""Top level API.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__
from .main import FastCS as FastCS
from .main import launch as launch

__all__ = ["__version__"]
