"""SystemCheck: tool and KVM detection, sudo probing."""

import subprocess
from pathlib import Path

from qemulab.utils.system import SystemCheck


def test_check_tools_all_present(monkeypatch):
    monkeypatch.setattr("qemulab.utils.system.shutil.which", lambda t: f"/usr/bin/{t}")
    assert SystemCheck.check_tools() is True


def test_check_tools_reports_missing(monkeypatch):
    monkeypatch.setattr(
        "qemulab.utils.system.shutil.which", lambda t: None if t == "tmux" else "/bin/x"
    )
    assert SystemCheck.check_tools() is False


def test_check_kvm(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda self: False)
    assert SystemCheck.check_kvm() is False
    monkeypatch.setattr(Path, "exists", lambda self: True)
    assert SystemCheck.check_kvm() is True


def test_sudo_with_cached_credentials_is_quiet(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    assert SystemCheck.warn_if_sudo_needs_password() is None
