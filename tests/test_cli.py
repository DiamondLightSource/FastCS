import subprocess
import sys

from fastcs import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs", "--version"]
    info = "INFO: PVXS QSRV2 is loaded, permitted, and ENABLED.\n"
    assert subprocess.check_output(cmd).decode().strip() == info + __version__
