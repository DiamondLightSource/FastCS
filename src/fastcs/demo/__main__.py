from fastcs import __version__
from fastcs.launch import launch

from .controllers import TemperatureController

launch(TemperatureController, version=__version__)
