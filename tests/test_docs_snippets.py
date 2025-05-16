import glob
import runpy
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).parent


@pytest.fixture(scope="module", autouse=True)
def sim_temperature_controller():
    config_path: str = f"{HERE}/../src/fastcs/demo/simulation/temp_controller.yaml"
    process = subprocess.Popen(
        ["tickit", "all", config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    TIMEOUT = 10
    start_time = time.monotonic()
    while process.stdout is not None:
        line = process.stdout.readline()
        if "Temperature controller running" in line:
            break

        if time.monotonic() - start_time > TIMEOUT:
            raise TimeoutError("Simulator did not start in time")

        time.sleep(0.1)

    yield

    process.kill()
    print(process.communicate()[0])


@pytest.mark.parametrize("filename", glob.glob("docs/snippets/*.py", recursive=True))
def test_snippet(filename):
    runpy.run_path(filename)
