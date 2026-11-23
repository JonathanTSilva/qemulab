"""Console helpers: alerts, panels, spinner, key handling and prompts, without a real TTY."""

import logging
import sys
import types
from unittest.mock import patch

import pytest
import typer
from rich.text import Text

from qemulab.utils import console


@pytest.mark.parametrize(
    ("func", "level"),
    [
        (console.success, logging.INFO),
        (console.warning, logging.WARNING),
        (console.debug, logging.DEBUG),
    ],
)
def test_simple_alerts_use_their_level(func, level):
    with patch("qemulab.utils.console._logger") as log:
        func("hello", {"k": "v"})
    assert log.log.call_args.args[0] == level
    assert log.log.call_args.kwargs["extra"]["extra_data"]["k"] == "v"


def test_log_alert_falls_back_to_raw_message_on_bad_markup():
    with patch("qemulab.utils.console._logger") as log:
        console.info("broken [/nope] markup")
    extra = log.log.call_args.kwargs["extra"]["extra_data"]
    assert "broken" in extra["raw_message"]


def test_log_alert_markup_failure_uses_original(monkeypatch):
    def boom(_msg):
        raise ValueError("bad")

    monkeypatch.setattr(console.Text, "from_markup", staticmethod(boom))
    with patch("qemulab.utils.console._logger") as log:
        console.info("plain")
    assert log.log.call_args.kwargs["extra"]["extra_data"]["raw_message"] == "plain"


def test_error_prints_traceback_when_asked():
    with (
        patch("qemulab.utils.console._logger"),
        patch.object(console.console_instance, "print") as pr,
    ):
        try:
            raise RuntimeError("kaboom")
        except RuntimeError:
            console.error("failed", exc_info=True)
    pr.assert_called_once()


def test_error_without_active_exception_prints_nothing():
    with (
        patch("qemulab.utils.console._logger"),
        patch.object(console.console_instance, "print") as pr,
    ):
        console.error("failed", exc_info=True)
    pr.assert_not_called()


def test_section_and_header_survive_missing_terminal(monkeypatch):
    def no_tty():
        raise OSError

    monkeypatch.setattr(console, "get_terminal_size", no_tty)
    with patch("qemulab.utils.console._logger") as log:
        console.section("title")
        console.header("title")
    assert log.info.call_count == 4


def test_panel_accepts_str_and_renderables():
    with patch.object(console.console_instance, "print") as pr:
        console.panel("[b]hi[/b]", title="[i]t[/i]")
        console.panel(Text("renderable"))
    assert pr.call_count == 2


def test_spinner_runs_body():
    ran = []
    with console.spinner("working"):
        ran.append(True)
    assert ran == [True]


class FakeStdin:
    def __init__(self, chars: str):
        self.chars = list(chars)

    def fileno(self) -> int:
        return 0

    def read(self, _n: int) -> str:
        return self.chars.pop(0)


@pytest.fixture
def raw_tty(monkeypatch):
    monkeypatch.setattr(console.termios, "tcgetattr", lambda fd: ["saved"])
    monkeypatch.setattr(console.termios, "tcsetattr", lambda *a: None)
    monkeypatch.setattr(console.tty, "setraw", lambda fd: None)

    def feed(chars: str):
        monkeypatch.setattr(sys, "stdin", FakeStdin(chars))

    return feed


@pytest.mark.parametrize(
    ("chars", "expected"),
    [("\r", "ENTER"), ("\x1b[A", "UP"), ("\x1b[B", "DOWN"), ("\x1b[C", ""), ("x", "")],
)
def test_get_key_unix(raw_tty, chars, expected):
    raw_tty(chars)
    assert console._get_key_unix() == expected


def test_get_key_unix_ctrl_c(raw_tty):
    raw_tty("\x03")
    with pytest.raises(KeyboardInterrupt):
        console._get_key_unix()


def test_get_key_dispatches_on_platform(monkeypatch):
    monkeypatch.setattr(console, "_get_key_unix", lambda: "UNIX")
    monkeypatch.setattr(console, "_get_key_windows", lambda: "WIN")
    monkeypatch.delitem(sys.modules, "msvcrt", raising=False)
    assert console._get_key() == "UNIX"
    monkeypatch.setitem(sys.modules, "msvcrt", types.ModuleType("msvcrt"))
    assert console._get_key() == "WIN"


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        ([b"\r"], "ENTER"),
        ([b"\xe0", b"H"], "UP"),
        ([b"\x00", b"P"], "DOWN"),
        ([b"\xe0", b"Z"], ""),
        ([b"a"], ""),
    ],
)
def test_get_key_windows(monkeypatch, keys, expected):
    fake = types.SimpleNamespace(getch=lambda: keys.pop(0))
    monkeypatch.setattr(console, "msvcrt", fake, raising=False)
    assert console._get_key_windows() == expected


def test_get_key_windows_ctrl_c(monkeypatch):
    fake = types.SimpleNamespace(getch=lambda: b"\x03")
    monkeypatch.setattr(console, "msvcrt", fake, raising=False)
    with pytest.raises(KeyboardInterrupt):
        console._get_key_windows()


def test_selection_rejects_empty_choices():
    with pytest.raises(ValueError, match="empty"):
        console.selection("pick", [])


def test_selection_navigates_and_selects(monkeypatch):
    keys = iter(["DOWN", "DOWN", "UP", "OTHER", "ENTER"])
    monkeypatch.setattr(console, "_get_key", lambda: next(keys))
    with patch("qemulab.utils.console._logger"):
        assert console.selection("pick", ["a", "b", "c"]) == "b"


def test_selection_wraps_upwards(monkeypatch):
    keys = iter(["UP", "ENTER"])
    monkeypatch.setattr(console, "_get_key", lambda: next(keys))
    with patch("qemulab.utils.console._logger"):
        assert console.selection("pick", ["a", "b", "c"]) == "c"


def test_selection_cancel_exits_cleanly(monkeypatch):
    def cancel():
        raise KeyboardInterrupt

    monkeypatch.setattr(console, "_get_key", cancel)
    with patch("qemulab.utils.console._logger"), pytest.raises(typer.Exit) as exc:
        console.selection("pick", ["a"])
    assert exc.value.exit_code == 0


def test_prompt_and_confirm_delegate_to_rich():
    with patch("qemulab.utils.console.Prompt.ask", return_value="answer") as ask:
        assert console.prompt("name?", default="d", secret=True, choices=["x"]) == "answer"
    assert ask.call_args.kwargs["password"] is True
    with patch("qemulab.utils.console.Confirm.ask", return_value=True) as ask:
        assert console.confirm("sure?", default=True) is True
    assert ask.call_args.kwargs["default"] is True
