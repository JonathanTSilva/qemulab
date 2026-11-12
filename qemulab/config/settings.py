import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

CONF_DIR = Path(__file__).parent
USER_CONFIG_ENV = "QEMULAB_CONFIG"
DEFAULT_USER_CONFIG = Path("~/.config/qemulab/config.yaml")


def default_scenarios_path() -> Path:
    """Trusted per-user scenarios dir: ${XDG_CONFIG_HOME:-~/.config}/qemulab/scenarios."""
    base = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(base).expanduser() / "qemulab" / "scenarios"


def _load_yaml(path: Path) -> dict[str, Any]:
    if path.is_file():
        with path.open() as f:
            return yaml.safe_load(f) or {}
    return {}


def user_config_path() -> Path:
    """Path of the user config file (QEMULAB_CONFIG, else ~/.config/qemulab/config.yaml)."""
    return Path(os.environ.get(USER_CONFIG_ENV) or DEFAULT_USER_CONFIG).expanduser()


def yaml_config_settings_source() -> dict[str, Any]:
    """Loads settings from the user config, falling back to the packaged defaults.yaml."""
    merged = _load_yaml(CONF_DIR / "defaults.yaml")
    merged.update(_load_yaml(user_config_path()))
    return merged


class MgmtNetwork(BaseModel):
    base_ip: str = Field("192.0.2.1", description="Management bridge IP")
    netmask: int = Field(24, description="Network mask CIDR")
    bridge_name: str = Field("br_qlab", description="Management bridge interface name")


class NetworkSettings(BaseModel):
    mgmt: MgmtNetwork = Field(default_factory=MgmtNetwork)
    data_bridge_name: str = Field("qlab_data", description="Data plane bridge interface name")


class CommonCommand(BaseModel):
    """A command that runs on all nodes regardless of scenario.

    The password is never defined in code. Supply it either inline in your user config
    (`password`) or, preferably, as the name of an environment variable (`password_env`).
    """

    command: str
    password: str | None = None
    password_env: str | None = None
    description: str = ""

    def resolved_password(self) -> str | None:
        """Return the password, reading it from the environment when `password_env` is set."""
        if self.password_env:
            value = os.environ.get(self.password_env)
            if value is None:
                msg = f"Environment variable {self.password_env} is not set"
                raise ValueError(msg)
            return value
        return self.password


class GuestCLISettings(BaseModel):
    """How to talk to the guest OS console. Every field is optional and has no default."""

    login_prompt: str = Field("login:", description="Text that signals the guest has booted")
    username: str | None = Field(None, description="Console login user (login skipped if unset)")
    password: str | None = Field(None, description="Console login password")
    enter_config_command: str | None = Field(None, description="Command to enter config mode")
    load_config_command: str | None = Field(
        None, description="Template to load the node config file, e.g. 'load {file}'"
    )
    commit_command: str | None = Field(None, description="Command to commit the configuration")
    exit_config_command: str | None = Field(None, description="Command to leave config mode")


class Settings(BaseSettings):
    """Global application configuration.

    Order of precedence:
    1. Environment variables (e.g., QEMULAB_DEFAULT_BOARD=board1)
    2. User config (~/.config/qemulab/config.yaml, or the path in QEMULAB_CONFIG)
    3. Packaged defaults.yaml
    4. Default values defined here
    """

    # Paths
    images_base_path: Path = Field(
        Path("~/qemulab/images"), description="Root path holding one directory per board"
    )
    flash_base_path: str | None = Field(
        None,
        description=(
            "Optional prefix for per-node flash dirs (node id is appended). "
            "Default: $XDG_RUNTIME_DIR/qemulab/flash_<n>, else a private temp dir"
        ),
    )
    scenarios_path: Path = Field(
        default_factory=default_scenarios_path,
        description=(
            "Root path for scenarios. Scenario commands are typed into guest consoles, so this "
            "must be a location only you can write to. "
            "Default: ${XDG_CONFIG_HOME:-~/.config}/qemulab/scenarios"
        ),
    )

    # Image discovery. Layout: <images_base_path>/<board_dir_template>/<images_subdir>/<kernel file>
    board_dir_pattern: str = Field(
        r"^(?P<board>[A-Za-z0-9_]+)$",
        description="Regex matching a board directory; the named group 'board' is the board name",
    )
    board_dir_template: str = Field(
        "{board}", description="Directory name for a board (inverse of board_dir_pattern)"
    )
    images_subdir: str = Field("images", description="Sub-directory holding kernel and initrd")
    kernel_pattern: str = Field(
        "{board}-bzImage-{version}", description="Kernel file name template"
    )
    initrd_pattern: str = Field(
        "{board}-rootfs.cpio-{version}", description="Initrd file name template"
    )
    guest_config_subdir: str = Field(
        "configs", description="Directory inside the flash storage receiving node configs"
    )

    # Defaults
    default_board: str | None = Field(None, description="Preselected board name")

    # Limits (Hard constraints)
    max_nodes_limit: int = Field(4, description="Maximum supported QEMU nodes")

    # Runtime
    tmux_session_name: str = "qemulab"
    log_level: str = "INFO"

    # Network Configuration
    network: NetworkSettings = Field(default_factory=NetworkSettings)

    # Guest console behaviour (login and config-mode commands)
    guest: GuestCLISettings = Field(default_factory=GuestCLISettings)

    # Commands executed on all nodes before scenario commands. No default: supply them in your
    # user config or via QEMULAB_COMMON_COMMANDS (JSON). Secrets should use `password_env`.
    common_commands: list[dict[str, Any]] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="QEMULAB_", env_nested_delimiter="__")

    @field_validator("images_base_path", "scenarios_path")
    @classmethod
    def _expand_user(cls, value: Path) -> Path:
        return value.expanduser()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            yaml_config_settings_source,
            init_settings,
        )

    def get_common_commands(self) -> list[CommonCommand]:
        """Convert raw common_commands dicts to typed CommonCommand objects"""
        return [CommonCommand(**cmd) for cmd in self.common_commands]


# Singleton instance
settings = Settings()
