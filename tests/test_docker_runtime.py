import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKER_COMPOSE_COMMAND = ["docker", "compose"]
UI_URL = "http://127.0.0.1:8000/ui"


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def _docker_daemon_is_available() -> bool:
    if shutil.which("docker") is None:
        return False

    docker_info = subprocess.run(
        ["docker", "info"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return docker_info.returncode == 0


def _wait_until_ui_is_ready(timeout_seconds: int = 60) -> bool:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with urlopen(UI_URL, timeout=2) as response:
                html = response.read().decode("utf-8")
                if response.status == 200 and "Support Agent" in html:
                    return True
        except (URLError, OSError, ConnectionResetError):
            time.sleep(1)

    return False


def test_docker_compose_can_serve_ui_runtime() -> None:
    """Optional integration test: validates docker compose runtime end-to-end."""
    if os.getenv("RUN_DOCKER_TESTS") != "1":
        pytest.skip("Set RUN_DOCKER_TESTS=1 to execute Docker runtime test.")

    if not _docker_daemon_is_available():
        pytest.skip("Docker daemon is not available on this machine.")

    if _is_port_in_use("127.0.0.1", 8000):
        pytest.skip("Port 8000 is busy. Stop local services and rerun Docker runtime test.")

    compose_up = subprocess.run(
        DOCKER_COMPOSE_COMMAND + ["up", "-d", "--build"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    try:
        assert compose_up.returncode == 0, compose_up.stdout + compose_up.stderr
        assert _wait_until_ui_is_ready(), "Docker container did not serve /ui within timeout."
    finally:
        subprocess.run(
            DOCKER_COMPOSE_COMMAND + ["down"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
