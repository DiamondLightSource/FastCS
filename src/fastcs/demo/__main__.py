from fastcs import __version__
from fastcs.launch import launch

from .controllers import TempController

launch(TempController, version=__version__)
