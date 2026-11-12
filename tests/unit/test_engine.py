"""Tests for the Engine orchestration service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qemulab.models.context import SessionContext
from qemulab.models.scenario import Command, Scenario, ScenarioConfig
from qemulab.services.engine import Engine, ScenarioAbortError


@pytest.fixture
def mock_context(tmp_path):
    """Creates a minimal SessionContext for testing."""
    scenario_path = tmp_path / "ospf"
    scenario_path.mkdir()

    # Create dummy config files
    for i in range(1, 3):
        cfg_file = scenario_path / f"cfg_dut{i}"
        cfg_file.write_text(f"config for dut{i}")

    scenario = Scenario(
        name="ospf", path=scenario_path, config=ScenarioConfig(description="Test scenario")
    )

    ctx = SessionContext(
        selected_board="board1",
        selected_version="1.0.0",
        selected_scenario=scenario,
        kernel_path=Path("k"),
        initrd_path=Path("i"),
    )
    ctx.set_manual_node_count(2)
    return ctx


@patch("qemulab.services.engine.NetworkService")
@patch("qemulab.services.engine.subprocess.run")
def test_prepare_environment(mock_run, mock_network, mock_context, tmp_path):
    """Test that prepare_environment sets up network and flash correctly."""
    # Setup
    engine = Engine(mock_context)

    # Mock settings.flash_base_path
    with patch("qemulab.services.engine.settings") as mock_settings:
        mock_settings.flash_base_path = str(tmp_path / "flash/flash_")

        # Execute
        engine.prepare_environment()

    # Verify network setup
    mock_network.cleanup.assert_called_once()
    mock_network.setup_management_bridge.assert_called_once()
    mock_network.setup_data_bridge.assert_called_once()

    # Verify tap interfaces created for each node
    assert mock_network.create_tap_interfaces.call_count == 2

    # Flash dirs and configs are created by the user, privately, without sudo
    for i in (1, 2):
        flash = tmp_path / f"flash/flash_{i}"
        assert flash.stat().st_mode & 0o777 == 0o700
        cfg = flash / mock_settings.guest_config_subdir / f"cfg_dut{i}"
        assert cfg.read_text() == f"config for dut{i}"
        assert cfg.stat().st_mode & 0o777 == 0o600
    mock_run.assert_not_called()


@patch("qemulab.services.engine.subprocess.run")
@patch("qemulab.services.engine.QemuCommandBuilder.build_command")
@patch("qemulab.services.engine.TmuxService")
def test_start_launches_qemu(mock_tmux_class, mock_build_cmd, mock_run, mock_context):
    """Test that start() launches QEMU instances in tmux."""
    # Setup
    mock_tmux = MagicMock()
    mock_tmux_class.return_value = mock_tmux
    mock_build_cmd.return_value = ["qemu-system-x86_64", "-nographic"]

    mock_run.return_value = MagicMock(returncode=0)
    mock_tmux.wait_for_text.return_value = True  # panes share the sudo timestamp
    mock_context.sudo_password = "test123"
    engine = Engine(mock_context)

    # Execute
    engine.start()

    # sudo is validated from Python, and the password never reaches the panes
    mock_run.assert_called_once_with(
        ["sudo", "-S", "-v"], input="test123\n", text=True, capture_output=True
    )
    assert all("test123" not in str(c) for c in mock_tmux.send_keys.call_args_list)

    # Verify tmux session created
    mock_tmux.create_session.assert_called_once()
    mock_tmux.setup_layout.assert_called_once_with(2)

    # Verify QEMU launched for each node
    assert mock_tmux.send_keys.call_count >= 2  # At least 2 nodes worth of commands


@patch("qemulab.services.engine.TmuxService")
@patch("qemulab.services.engine.settings")
def test_configure_nodes_smart_polling(mock_settings, mock_tmux_class, mock_context):
    """Test that configure_nodes waits for boot and applies config."""
    # Setup
    mock_tmux = MagicMock()
    mock_tmux_class.return_value = mock_tmux
    mock_tmux.wait_for_text.return_value = True  # Simulate successful boot

    # Mock common commands and guest console settings
    mock_settings.get_common_commands.return_value = []
    mock_settings.guest.login_prompt = "login:"
    mock_settings.guest.username = "labuser"
    mock_settings.guest.password = "labpass"
    mock_settings.guest.enter_config_command = None
    mock_settings.guest.load_config_command = None
    mock_settings.guest.commit_command = None
    mock_settings.guest.exit_config_command = None

    engine = Engine(mock_context)

    # Execute
    engine.configure_nodes()

    # Verify boot detection was attempted for each node
    assert mock_tmux.wait_for_text.call_count == 2

    # Verify login sequence sent
    calls = mock_tmux.send_keys.call_args_list
    # Should contain the configured username and password for each node
    assert len([c for c in calls if c[0][1] == "labuser"]) == 2
    assert len([c for c in calls if c[0][1] == "labpass"]) == 2


@patch("qemulab.services.engine.subprocess.run")
@patch("qemulab.services.engine.QemuCommandBuilder.build_command")
@patch("qemulab.services.engine.TmuxService")
def test_start_falls_back_to_redacted_password(
    mock_tmux_class, mock_build_cmd, mock_run, mock_context
):
    """If the pane can't share the sudo timestamp, the password is sent as sensitive."""
    mock_tmux = MagicMock()
    mock_tmux_class.return_value = mock_tmux
    mock_tmux.wait_for_text.return_value = False
    mock_build_cmd.return_value = ["qemu-system-x86_64"]
    mock_run.return_value = MagicMock(returncode=0)
    mock_context.sudo_password = "s3cret pw"

    with patch("qemulab.services.engine.time.sleep"):
        Engine(mock_context).start()

    with_pw = [c for c in mock_tmux.send_keys.call_args_list if "s3cret" in str(c.args)]
    assert len(with_pw) == 2  # one per node
    for call in with_pw:
        assert call.kwargs == {"sensitive": True}
        assert call.args[1].startswith(" ")  # leading space: not stored in history
    exports = [c for c in mock_tmux.send_keys.call_args_list if "HISTCONTROL=ignorespace" in str(c)]
    assert len(exports) == 2


@patch("qemulab.services.engine.subprocess.run")
@patch("qemulab.services.engine.TmuxService")
def test_start_aborts_on_bad_sudo_password(mock_tmux_class, mock_run, mock_context):
    mock_run.return_value = MagicMock(returncode=1)
    mock_context.sudo_password = "wrong"
    with pytest.raises(RuntimeError):
        Engine(mock_context).start()
    mock_tmux_class.return_value.create_session.assert_not_called()


@patch("qemulab.services.engine.NetworkService")
@patch("qemulab.services.engine.subprocess.run")
def test_prepare_environment_refuses_symlinked_flash_dir(
    mock_run, mock_network, mock_context, tmp_path
):
    """A symlinked flash dir must never reach `sudo rm -rf`."""
    target = tmp_path / "victim"
    target.mkdir()
    real = tmp_path / "flash"
    real.mkdir()
    (real / "flash_1").symlink_to(target)

    with patch("qemulab.services.engine.settings") as mock_settings:
        mock_settings.flash_base_path = str(real / "flash_")
        mock_settings.guest_config_subdir = "config"
        with pytest.raises(OSError):
            Engine(mock_context).prepare_environment()

    assert target.exists()
    mock_run.assert_not_called()


def _scenario_settings(mock_settings):
    mock_settings.get_common_commands.return_value = []
    mock_settings.guest.enter_config_command = None
    mock_settings.guest.load_config_command = None
    mock_settings.guest.commit_command = None
    mock_settings.guest.exit_config_command = None


def _ctx_with_commands(mock_context):
    mock_context.selected_scenario.config.commands = [Command(command="show version")]
    return mock_context


@pytest.mark.parametrize("proc", ["qemu-system-x86_64", "sudo"])
@patch("qemulab.services.engine.time.sleep")
@patch("qemulab.services.engine.TmuxService")
@patch("qemulab.services.engine.settings")
def test_scenario_commands_sent_when_pane_runs_qemu(
    mock_settings, mock_tmux_class, _sleep, proc, mock_context
):
    _scenario_settings(mock_settings)
    mock_tmux = mock_tmux_class.return_value
    mock_tmux.pane_current_command.return_value = proc

    Engine(_ctx_with_commands(mock_context))._apply_node_config(1, 0)

    mock_tmux.send_keys.assert_called_once_with(0, "show version")


@pytest.mark.parametrize("proc", ["bash", "zsh", None])
@patch("qemulab.services.engine.time.sleep")
@patch("qemulab.services.engine.TmuxService")
@patch("qemulab.services.engine.settings")
def test_scenario_aborted_when_pane_runs_something_else(
    mock_settings, mock_tmux_class, _sleep, proc, mock_context
):
    _scenario_settings(mock_settings)
    mock_tmux = mock_tmux_class.return_value
    mock_tmux.pane_current_command.return_value = proc

    with pytest.raises(ScenarioAbortError, match="expected QEMU"):
        Engine(_ctx_with_commands(mock_context))._apply_node_config(1, 0)

    mock_tmux.send_keys.assert_not_called()
