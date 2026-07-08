import shutil
import subprocess

import pytest

from scripts import docker


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


@pytest.mark.docker
def test_docker_smoke_e2e():
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    docker.smoke()
