import glob
import runpy
import signal
import subprocess
from pathlib import Path
from time import sleep

import pytest

HERE = Path(__file__).parent


@pytest.fixture(scope="module", autouse=True)
def sim_temperature_controller():
    """Subprocess that runs ``tickit all <config_path>``."""
    config_path: str = f"{HERE}/../src/fastcs/demo/simulation/temp_controller.yaml"
    proc = subprocess.Popen(
        ["tickit", "all", config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    sleep(1)

    yield

    proc.send_signal(signal.SIGINT)
    print(proc.communicate()[0])


@pytest.mark.parametrize("filename", glob.glob("docs/snippets/*.py", recursive=True))
def test_snippet(filename):
    runpy.run_path(filename)
