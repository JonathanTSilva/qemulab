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
