"""Tests for TmuxService logging hygiene."""

import subprocess
from unittest.mock import patch

import pytest

from qemulab.services.tmux import TmuxService


@pytest.fixture
def tmux():
    svc = TmuxService("t")
    svc.tmux_bin = "tmux"
    svc.pane_ids = ["%0"]
    return svc


def _logged(mock_logger) -> str:
    return " ".join(str(c) for c in mock_logger.method_calls)


def test_send_keys_sensitive_is_redacted(tmux):
    with patch.object(subprocess, "run"), patch("qemulab.services.tmux.logger") as log:
        tmux.send_keys(0, "hunter2", sensitive=True)
    assert "hunter2" not in _logged(log)
    assert "<redacted>" in _logged(log)


def test_sensitive_failure_does_not_leak_secret(tmux):
    err = subprocess.CalledProcessError(1, ["tmux", "send-keys", "hunter2"], stderr="boom")
    with (
        patch.object(subprocess, "run", side_effect=err),
        patch("qemulab.services.tmux.logger") as log,
        pytest.raises(subprocess.CalledProcessError) as exc,
    ):
        tmux.send_keys(0, "hunter2", sensitive=True)
    assert "hunter2" not in _logged(log)
    assert "hunter2" not in str(exc.value)


def test_pane_current_command(tmux):
    with patch.object(subprocess, "run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="qemu-system-x86\n", stderr="")
        assert tmux.pane_current_command(0) == "qemu-system-x86"
    args = run.call_args.args[0]
    assert args[:4] == ["tmux", "display-message", "-p", "-t"]
    assert "#{pane_current_command}" in args


def test_pane_current_command_unknown_pane(tmux):
    assert tmux.pane_current_command(5) is None
