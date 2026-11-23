"""TmuxService behaviour against a fake `tmux` binary (no real tmux, no real sleeping)."""

import subprocess

import pytest

from qemulab.services.tmux import TmuxService


class FakeTmux:
    """Stands in for subprocess.run: records calls and answers per tmux sub-command."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.fail_on: set[str] = set()
        self.has_session = False
        self.pane_counter = 0
        self.capture_outputs: list[str] = []
        self.display_output = ""
        self.raise_on: dict[str, Exception] = {}

    def __call__(self, cmd, check=True, capture_output=True, text=True):
        self.calls.append(cmd)
        sub = cmd[1]
        if sub in self.raise_on:
            raise self.raise_on[sub]
        if sub in self.fail_on or (sub == "has-session" and not self.has_session):
            if check:
                raise subprocess.CalledProcessError(1, cmd, stderr="boom\n")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        out = ""
        if sub in ("new-session", "split-window"):
            out = f"%{self.pane_counter}\n"
            self.pane_counter += 1
        elif sub == "capture-pane":
            out = self.capture_outputs.pop(0) if self.capture_outputs else ""
        elif sub == "display-message":
            out = self.display_output
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    def subs(self) -> list[str]:
        return [c[1] for c in self.calls]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def fake(monkeypatch):
    fake = FakeTmux()
    monkeypatch.setattr(subprocess, "run", fake)
    monkeypatch.setattr("qemulab.services.tmux.time.sleep", lambda _s: None)
    return fake


@pytest.fixture
def tmux(fake):
    svc = TmuxService("sess")
    svc.tmux_bin = "tmux"
    return svc


def test_run_failure_is_logged_and_reraised(tmux, fake):
    fake.fail_on.add("kill-session")
    with pytest.raises(subprocess.CalledProcessError):
        tmux._run(["kill-session", "-t", "sess"])


def test_run_failure_without_check_is_quiet_and_returns_output(tmux, fake):
    fake.fail_on.add("kill-session")
    assert tmux._run(["kill-session"], check=False) == ""


def test_create_session_fresh(tmux, fake):
    tmux.create_session()
    assert tmux.pane_ids == ["%0"]
    assert fake.subs() == ["has-session", "new-session", "set-option", "set-option"]


def test_create_session_kills_existing(tmux, fake):
    fake.has_session = True
    tmux.create_session()
    assert fake.subs()[:3] == ["has-session", "kill-session", "new-session"]


def test_create_session_survives_kill_failure(tmux, fake):
    fake.has_session = True
    fake.raise_on["kill-session"] = RuntimeError("gone")
    tmux.create_session()
    assert tmux.pane_ids == ["%0"]


def test_session_exists(tmux, fake):
    assert tmux.session_exists() is False
    fake.has_session = True
    assert tmux.session_exists() is True


def test_setup_layout_single_node_does_nothing(tmux, fake):
    tmux.pane_ids = ["%0"]
    tmux.setup_layout(1)
    assert fake.calls == []


def test_setup_layout_two_nodes(tmux, fake):
    tmux.pane_ids = ["%0"]
    tmux.setup_layout(2)
    assert len(tmux.pane_ids) == 2
    assert fake.subs() == ["split-window", "select-layout"]


def test_setup_layout_four_nodes(tmux, fake):
    tmux.pane_ids = ["%0"]
    tmux.setup_layout(4)
    assert len(tmux.pane_ids) == 4
    assert fake.subs().count("split-window") == 3
    assert fake.subs()[-1] == "select-layout"


def test_setup_layout_split_failure_is_tolerated(tmux, fake):
    tmux.pane_ids = ["%0"]
    fake.fail_on.add("split-window")
    tmux.setup_layout(4)
    assert tmux.pane_ids == ["%0"]


def test_send_keys_targets_pane(tmux, fake):
    tmux.pane_ids = ["%0", "%1"]
    tmux.send_keys(1, "ls")
    assert fake.calls[-1] == ["tmux", "send-keys", "-t", "%1", "ls", "C-m"]


def test_send_keys_unknown_pane_is_ignored(tmux, fake):
    tmux.pane_ids = ["%0"]
    tmux.send_keys(3, "ls")
    assert fake.calls == []


def test_pane_current_command_swallows_errors(tmux, fake):
    tmux.pane_ids = ["%0"]
    fake.raise_on["display-message"] = RuntimeError("nope")
    assert tmux.pane_current_command(0) is None


def test_pane_current_command_empty_output_is_none(tmux, fake):
    tmux.pane_ids = ["%0"]
    fake.display_output = "  \n"
    assert tmux.pane_current_command(0) is None


def test_clear_history(tmux, fake):
    tmux.pane_ids = ["%0"]
    tmux.clear_history(0)
    tmux.clear_history(9)
    assert fake.subs() == ["clear-history"]


def test_wait_for_text_unknown_pane(tmux):
    tmux.pane_ids = []
    assert tmux.wait_for_text(0, "x") is False


def test_wait_for_text_found_after_polling(tmux, fake, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr("qemulab.services.tmux.time", clock)
    tmux.pane_ids = ["%0"]
    fake.capture_outputs = ["", "", "", "", "", "login: ready"]
    assert tmux.wait_for_text(0, "login:", timeout=60, poll_interval=1.0) is True


def test_wait_for_text_read_error_then_timeout(tmux, fake, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr("qemulab.services.tmux.time", clock)
    tmux.pane_ids = ["%0"]
    fake.raise_on["capture-pane"] = RuntimeError("pane gone")
    assert tmux.wait_for_text(0, "never", timeout=3, poll_interval=1.0) is False


def test_wait_for_text_timeout_logs_last_output(tmux, fake, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr("qemulab.services.tmux.time", clock)
    tmux.pane_ids = ["%0"]
    assert tmux.wait_for_text(0, "never", timeout=2, poll_interval=1.0) is False
