from pathlib import Path

import pytest

from qemulab.config.settings import CommonCommand, Settings
from qemulab.models.scenario import ScenarioConfig


def test_settings_load_defaults():
    """Ensure settings load defaults.yaml values."""
    s = Settings()
    # Check a default value we defined
    assert s.network.mgmt.base_ip == "192.0.2.1"
    # Check that the path type conversion worked and "~" is expanded
    assert isinstance(s.images_base_path, Path)
    assert "~" not in str(s.images_base_path)
    # No secrets or credentials ship by default
    assert s.common_commands == []
    assert s.guest.username is None
    assert s.guest.password is None


def test_scenarios_path_defaults_to_user_config_dir(tmp_path, monkeypatch):
    """Scenarios default to a per-user location, never the current directory."""
    monkeypatch.delenv("QEMULAB_SCENARIOS_PATH", raising=False)
    monkeypatch.setenv("QEMULAB_CONFIG", str(tmp_path / "none.yaml"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    assert Settings().scenarios_path == tmp_path / "xdg" / "qemulab" / "scenarios"

    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert Settings().scenarios_path == tmp_path / "home" / ".config" / "qemulab" / "scenarios"


def test_scenarios_path_overridable(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"scenarios_path: {tmp_path / 'from_cfg'}\n")
    monkeypatch.setenv("QEMULAB_CONFIG", str(cfg))
    assert Settings().scenarios_path == tmp_path / "from_cfg"

    monkeypatch.setenv("QEMULAB_SCENARIOS_PATH", str(tmp_path / "from_env"))
    assert Settings().scenarios_path == tmp_path / "from_env"


def test_common_command_password_from_env(monkeypatch):
    """Passwords are resolved from the environment, never from code."""
    cmd = CommonCommand(command="enable debug", password_env="QEMULAB_TEST_SECRET")
    monkeypatch.setenv("QEMULAB_TEST_SECRET", "s3cret")
    assert cmd.resolved_password() == "s3cret"
    monkeypatch.delenv("QEMULAB_TEST_SECRET")
    with pytest.raises(ValueError, match="QEMULAB_TEST_SECRET"):
        cmd.resolved_password()


def test_user_config_overrides_defaults(tmp_path, monkeypatch):
    """A user config file is merged over the packaged defaults."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "default_board: board7\n"
        "common_commands:\n"
        "  - command: enable debug\n"
        "    password_env: MY_SECRET\n"
    )
    monkeypatch.setenv("QEMULAB_CONFIG", str(cfg))
    s = Settings()
    assert s.default_board == "board7"
    assert s.get_common_commands()[0].password_env == "MY_SECRET"


def test_scenario_config_parsing():
    """Ensure ScenarioConfig parses the JSON structure correctly."""
    raw_json = {
        "description": "Test Topology",
        "commands": [{"command": "conf t", "description": "Enter config"}],
    }
    model = ScenarioConfig(**raw_json)
    assert model.description == "Test Topology"
    assert model.commands[0].command == "conf t"


def test_scenario_config_defaults():
    """Ensure optional fields default correctly."""
    raw_json = {"description": "Minimal"}
    model = ScenarioConfig(**raw_json)
    assert model.commands == []
