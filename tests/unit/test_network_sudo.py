"""NetworkService: sudo plumbing and bridge/tap idempotency, with a fake runner."""

import subprocess

import pytest

from qemulab.config.settings import settings
from qemulab.services.network import NetworkService


class FakeProc:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.inputs: list[bytes] = []

    def communicate(self, input=None):
        self.inputs.append(input)


def test_run_sudo_with_password_feeds_stdin(monkeypatch):
    procs = []

    def fake_popen(cmd, **kwargs):
        proc = FakeProc(0)
        proc.cmd = cmd
        procs.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    assert NetworkService.run_sudo(["ip", "a"], sudo_password="pw") is True
    assert procs[0].cmd == ["sudo", "-S", "ip", "a"]
    assert procs[0].inputs == [b"pw\n"]


def test_run_sudo_with_password_reports_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: FakeProc(1))
    assert NetworkService.run_sudo(["ip", "a"], sudo_password="pw") is False


@pytest.mark.parametrize("check", [True, False])
def test_run_sudo_failure_returns_false(monkeypatch, check):
    def boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", boom)
    assert NetworkService.run_sudo(["ip", "a"], check=check) is False


def test_run_sudo_success(monkeypatch):
    seen = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    assert NetworkService.run_sudo(["ip", "a"]) is True
    assert seen == [["sudo", "ip", "a"]]


@pytest.fixture
def commands(monkeypatch):
    """Record run_sudo commands; `existing` holds interface names that 'exist'."""

    class Recorder:
        def __init__(self):
            self.cmds: list[list[str]] = []
            self.existing: set[str] = set()

    rec = Recorder()

    def fake_run_sudo(cmd, check=True, sudo_password=None):
        rec.cmds.append(cmd)
        if cmd[:3] == ["ip", "link", "show"]:
            return cmd[3] in rec.existing
        return True

    monkeypatch.setattr(NetworkService, "run_sudo", staticmethod(fake_run_sudo))
    return rec


def test_management_bridge_already_present(commands):
    commands.existing.add(settings.network.mgmt.bridge_name)
    NetworkService.setup_management_bridge()
    assert len(commands.cmds) == 1


def test_data_bridge_created_with_default_name(commands):
    NetworkService.setup_data_bridge()
    assert ["ip", "link", "add", "name", settings.network.data_bridge_name, "type", "bridge"] in (
        commands.cmds
    )
    assert commands.cmds[-1][-1] == "up"


def test_data_bridge_custom_name_skipped_when_present(commands):
    commands.existing.add("custom")
    NetworkService.setup_data_bridge("custom")
    assert len(commands.cmds) == 1


def test_create_tap_interfaces_skips_existing(commands):
    commands.existing.update({"tap_qlab1_0", "tap_qlab1_1"})
    NetworkService.create_tap_interfaces(1)
    assert len(commands.cmds) == 2  # two existence checks only


def test_create_tap_interfaces_creates_both(commands):
    NetworkService.create_tap_interfaces(2)
    adds = [c for c in commands.cmds if c[:3] == ["ip", "tuntap", "add"]]
    assert [c[4] for c in adds] == ["tap_qlab2_0", "tap_qlab2_1"]


def test_cleanup_deletes_taps_and_bridges(commands):
    NetworkService.cleanup(node_count=2)
    deleted = [c[-1] for c in commands.cmds if c[:3] == ["ip", "link", "delete"]]
    assert deleted == [
        "tap_qlab1_0",
        "tap_qlab1_1",
        "tap_qlab2_0",
        "tap_qlab2_1",
        settings.network.data_bridge_name,
        settings.network.mgmt.bridge_name,
    ]
