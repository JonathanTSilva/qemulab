"""Tests for the startup system checks."""

import subprocess
from unittest.mock import patch

from qemulab.utils.system import SystemCheck


def test_sudo_password_requirement_only_warns():
    error = subprocess.CalledProcessError(1, "sudo")
    with patch("qemulab.utils.system.subprocess.run", side_effect=error):
        assert SystemCheck.warn_if_sudo_needs_password() is None


def test_check_all_ignores_sudo_warning():
    with (
        patch.object(SystemCheck, "check_tools", return_value=True),
        patch.object(SystemCheck, "check_kvm", return_value=True),
        patch.object(SystemCheck, "warn_if_sudo_needs_password") as warn,
    ):
        assert SystemCheck.check_all() is True
    warn.assert_called_once()


def test_check_all_fails_when_a_check_fails():
    with (
        patch.object(SystemCheck, "check_tools", return_value=True),
        patch.object(SystemCheck, "check_kvm", return_value=False),
        patch.object(SystemCheck, "warn_if_sudo_needs_password"),
    ):
        assert SystemCheck.check_all() is False
