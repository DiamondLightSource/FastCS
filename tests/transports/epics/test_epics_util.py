import pytest
from pvi.device import SignalR
from pydantic import ValidationError

from fastcs.util import snake_to_pascal


def test_pvi_validation_error():
    name = snake_to_pascal("Name-With_%_Invalid-&-Symbols_£_")
    with pytest.raises(ValidationError):
        SignalR(name=name, read_pv="test")
