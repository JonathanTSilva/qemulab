"""Engine: sudo helpers, flash cleanup, login and config-mode sequences (fake tmux, no sleeping)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qemulab.config.settings import CommonCommand, settings
from qemulab.models.context import SessionContext
from qemulab.models.scenario import Command, Scenario, ScenarioConfig
from qemulab.services.engine import Engine


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("qemulab.services.engine.time.sleep"):
        yield


@pytest.fixture
def ctx(tmp_path):
    path = tmp_path / "scn"
    path.mkdir()
    (path / "cfg_dut1").write_text("c1")
    scenario = Scenario(name="scn", path=path, config=ScenarioConfig(description="d"))
    return SessionContext(
        selected_board="b",
        selected_scenario=scenario,
        kernel_path=Path("k"),
        initrd_path=Path("i"),
    )


@pytest.fixture
def engine(ctx):
    with patch("qemulab.services.engine.TmuxService") as tmux_cls:
        eng = Engine(ctx)
        eng.tmux = tmux_cls.return_value
        yield eng


def test_sudo_feeds_password_on_stdin(engine):
    engine.ctx.sudo_password = "pw"
    with patch("qemulab.services.engine.subprocess.run") as run:
        engine._sudo(["rm", "-rf", "/x"])
    assert run.call_args.args[0] == ["sudo", "-S", "rm", "-rf", "/x"]
    assert run.call_args.kwargs["input"] == b"pw\n"


def test_sudo_without_password(engine):
    with patch("qemulab.services.engine.subprocess.run") as run:
        engine._sudo(["true"])
    run.assert_called_once_with(["sudo", "true"], check=True)


def test_prepare_environment_removes_old_flash_dir_via_sudo(engine, tmp_path):
    flash_dir = tmp_path / "flash_1"
    flash_dir.mkdir()
    with (
        patch("qemulab.services.engine.NetworkService"),
        patch("qemulab.services.engine.subprocess.run") as run,
        patch("qemulab.services.engine.settings") as mock_settings,
        patch("qemulab.services.engine.remove_tree") as remove,
    ):
        mock_settings.flash_base_path = str(tmp_path / "flash_")
        mock_settings.guest_config_subdir = "cfg"
        engine.prepare_environment()
        remove.assert_called_once()
        remove.call_args.args[1](flash_dir)  # the sudo callback
    run.assert_called_once_with(["sudo", "rm", "-rf", str(flash_dir)], check=True)


def test_pane_has_sudo(engine):
    engine.tmux.wait_for_text.return_value = True
    assert engine._pane_has_sudo(0) is True
    engine.tmux.wait_for_text.return_value = False
    assert engine._pane_has_sudo(0) is False


def test_validate_sudo_success(engine):
    engine.ctx.sudo_password = "pw"
    with patch("qemulab.services.engine.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0)
        engine._validate_sudo()


def test_configure_nodes_skips_nodes_that_never_boot(engine, monkeypatch):
    engine.tmux.wait_for_text.return_value = False
    apply = MagicMock()
    monkeypatch.setattr(engine, "_apply_node_config", apply)
    engine.configure_nodes()
    apply.assert_not_called()


def test_configure_nodes_login_without_password(engine, monkeypatch):
    engine.tmux.wait_for_text.return_value = True
    monkeypatch.setattr(settings.guest, "username", "root")
    monkeypatch.setattr(settings.guest, "password", None)
    monkeypatch.setattr(engine, "_apply_node_config", MagicMock())
    engine.configure_nodes()
    engine.tmux.send_keys.assert_called_once_with(0, "root")


def test_apply_node_config_full_sequence(engine, monkeypatch, ctx):
    engine.tmux.pane_current_command.return_value = "qemu-system-x86_64"
    guest = settings.guest
    monkeypatch.setattr(guest, "enter_config_command", "configure")
    monkeypatch.setattr(guest, "load_config_command", "load {file}")
    monkeypatch.setattr(guest, "commit_command", "commit")
    monkeypatch.setattr(guest, "exit_config_command", "exit")
    monkeypatch.setenv("QLAB_TEST_PW", "envpw")
    monkeypatch.setattr(
        settings,
        "common_commands",
        [
            {"command": "set a", "password_env": "QLAB_TEST_PW"},
            {"command": "set b"},
        ],
    )
    assert all(isinstance(c, CommonCommand) for c in settings.get_common_commands())
    ctx.selected_scenario.config.commands = [Command(command="show x", description="d")]

    engine._apply_node_config(1, 0)

    sent = [c.args[1] for c in engine.tmux.send_keys.call_args_list]
    assert sent == [
        "configure",
        "load cfg_dut1",
        "set a",
        "envpw",
        "set b",
        "show x",
        "commit",
        "exit",
    ]
    pw_call = engine.tmux.send_keys.call_args_list[3]
    assert pw_call.kwargs == {"sensitive": True}
