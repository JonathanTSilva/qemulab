import logging
import subprocess
from unittest.mock import patch

import pytest

from qemulab.config.settings import settings
from qemulab.services.network import NetworkService


@pytest.fixture(autouse=True)
def silence_network_logger():
    """
    Automatically suppresses DEBUG logs from the NetworkService during tests.
    This prevents 'Command failed: ...' noise when we intentionally test failure paths.
    """
    logger = logging.getLogger("qemulab.services.network")
    previous_level = logger.level

    # Only show WARNING or higher (hides DEBUG "Command failed")
    logger.setLevel(logging.WARNING)

    yield

    # Restore original level after test
    logger.setLevel(previous_level)


@patch("subprocess.run")
def test_setup_management_bridge_creates_if_missing(mock_run):
    """If bridge doesn't exist, it should be created and IP assigned."""

    class MockProc:
        returncode = 0
        stderr = b""
        stdout = b""

    def side_effect(cmd, **kwargs):
        # Logic: if checking existence, pretend it's missing (returncode 1)
        if "show" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"Device not found")
        return MockProc()

    mock_run.side_effect = side_effect

    NetworkService.setup_management_bridge()

    # Verify sequence of commands
    calls = mock_run.call_args_list
    cmd_add = calls[1][0][0]
    assert "add" in cmd_add
    assert settings.network.mgmt.bridge_name in cmd_add

    cmd_addr = calls[3][0][0]
    expected_ip = f"{settings.network.mgmt.base_ip}/{settings.network.mgmt.netmask}"
    assert expected_ip in cmd_addr


@patch("subprocess.run")
def test_create_tap_interfaces(mock_run):
    """Ensure two taps are created per node and attached to correct bridges."""

    def side_effect(cmd, **kwargs):
        if "show" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"Device not found")
        return True

    mock_run.side_effect = side_effect

    NetworkService.create_tap_interfaces(1)

    # We expect creation of tap_qlab1_0 and tap_qlab1_1
    created_taps = []
    for call_obj in mock_run.call_args_list:
        cmd = call_obj[0][0]
        # Look for the 'ip tuntap add' command
        if "tuntap" in cmd and "add" in cmd:
            # Index 5 is the interface name
            created_taps.append(cmd[5])

    assert "tap_qlab1_0" in created_taps
    assert "tap_qlab1_1" in created_taps
