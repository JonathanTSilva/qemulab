import logging
import shlex
import shutil
import subprocess
import time

from qemulab.config.settings import settings
from qemulab.models.context import SessionContext
from qemulab.services.network import NetworkService
from qemulab.services.qemu import QemuCommandBuilder
from qemulab.services.tmux import TmuxService
from qemulab.utils.paths import ensure_private_dir, flash_dir_for, remove_tree

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, context: SessionContext):
        self.ctx = context
        self.tmux = TmuxService(settings.tmux_session_name)

    def _sudo(self, cmd: list[str]):
        """Helper to run host-side shell commands with sudo."""
        if self.ctx.sudo_password:
            # Feed the password on stdin: no shell, nothing visible in the process list
            subprocess.run(
                ["sudo", "-S", *cmd],
                input=f"{self.ctx.sudo_password}\n".encode(),
                check=True,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(["sudo"] + cmd, check=True)

    def prepare_environment(self):
        """Prepares physical resources (Network, Flash)."""
        NetworkService.cleanup(sudo_password=self.ctx.sudo_password)
        NetworkService.setup_management_bridge(sudo_password=self.ctx.sudo_password)
        if self.ctx.node_count > 1:
            NetworkService.setup_data_bridge(sudo_password=self.ctx.sudo_password)

        for i in range(1, self.ctx.node_count + 1):
            NetworkService.create_tap_interfaces(i, sudo_password=self.ctx.sudo_password)

            flash_dir = flash_dir_for(i, settings.flash_base_path)
            if flash_dir.exists():
                logger.info(f"Removing old flash directory: {flash_dir}")
                remove_tree(flash_dir, lambda p: self._sudo(["rm", "-rf", str(p)]))

            # Everything below is created by the current user (no sudo, no chmod 777/666).
            # QEMU runs as root and can read/write user-owned 0700 dirs anyway.
            config_dest = flash_dir / settings.guest_config_subdir
            logger.info(f"Creating flash structure: {config_dest}")
            ensure_private_dir(flash_dir)
            config_dest.mkdir(parents=True, exist_ok=True)

            if self.ctx.selected_scenario:
                src_cfg = self.ctx.selected_scenario.dut_files.get(i)
                if src_cfg and src_cfg.exists():
                    dst_cfg = config_dest / f"cfg_dut{i}"
                    logger.info(f"Copying config to {dst_cfg}")
                    shutil.copyfile(src_cfg, dst_cfg)
                    dst_cfg.chmod(0o600)

    def _validate_sudo(self) -> None:
        """Validate sudo from Python so panes can reuse the cached timestamp."""
        proc = subprocess.run(
            ["sudo", "-S", "-v"],
            input=f"{self.ctx.sudo_password}\n",
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError("sudo authentication failed")

    def _pane_has_sudo(self, pane_idx: int) -> bool:
        """True when the pane's shell shares the cached sudo timestamp (no tty_tickets split)."""
        self.tmux.send_keys(
            pane_idx,
            "sudo -n true && printf 'QLAB_%s\\n' SUDO_OK || printf 'QLAB_%s\\n' SUDO_NO",
        )
        return bool(self.tmux.wait_for_text(pane_idx, "QLAB_SUDO_OK", timeout=5, poll_interval=0.5))

    def _pane_sudo_fallback(self, pane_idx: int) -> None:
        """Type the password into the pane (last resort). Leading space + ignorespace keep it
        out of shell history, and it is never logged."""
        assert self.ctx.sudo_password is not None
        self.tmux.send_keys(pane_idx, " export HISTCONTROL=ignorespace")
        self.tmux.send_keys(
            pane_idx,
            f" printf '%s\\n' {shlex.quote(self.ctx.sudo_password)} | sudo -S -v",
            sensitive=True,
        )
        time.sleep(0.5)
        self.tmux.send_keys(pane_idx, " clear")
        self.tmux.clear_history(pane_idx)

    def start(self):
        """Launches the environment inside Tmux."""
        logger.info("Initializing Tmux session...")
        if self.ctx.sudo_password:
            self._validate_sudo()
        self.tmux.create_session()
        self.tmux.setup_layout(self.ctx.node_count)

        for i in range(1, self.ctx.node_count + 1):
            pane_idx = i - 1

            # Step 1: the pane reuses the sudo timestamp validated above; only if it can't
            # be shared (tty_tickets) do we fall back to typing the password (redacted).
            if self.ctx.sudo_password and not self._pane_has_sudo(pane_idx):
                logger.warning(
                    f"Pane {pane_idx} cannot share the sudo timestamp (tty_tickets); "
                    "using fallback. A sudoers rule is recommended (see README)."
                )
                self._pane_sudo_fallback(pane_idx)

            # Step 2: Launch QEMU
            # Sudo is now primed (valid for 15 mins by default), so this won't prompt
            cmd_list = QemuCommandBuilder.build_command(i, self.ctx)
            qemu_cmd_str = " ".join(cmd_list).replace("\n", " ")
            full_cmd = f"sudo {qemu_cmd_str}"

            logger.info(f"Launching QEMU Node {i} in Pane {pane_idx}")
            self.tmux.send_keys(pane_idx, full_cmd)

    def configure_nodes(self):
        """Waits for nodes to boot and applies configuration."""
        logger.info("Waiting for nodes to boot (Smart Polling)...")

        # Wait for ALL nodes to reach login prompt first
        boot_status = {}
        for i in range(1, self.ctx.node_count + 1):
            pane_idx = i - 1
            logger.info(f"Waiting for Node {i} boot...")

            # Wait for the guest login prompt (configurable)
            if self.tmux.wait_for_text(
                pane_idx, settings.guest.login_prompt, timeout=120, poll_interval=1.0
            ):
                logger.info(f"Node {i} boot detected - login prompt ready")
                boot_status[i] = True
                # Small delay to let the prompt fully stabilize
                time.sleep(1)
            else:
                logger.error(f"Node {i} timed out waiting for boot.")
                boot_status[i] = False

        # Now configure all successfully booted nodes
        for i in range(1, self.ctx.node_count + 1):
            if not boot_status.get(i):
                logger.warning(f"Skipping configuration for Node {i} (boot failed)")
                continue

            pane_idx = i - 1
            logger.info(f"Configuring Node {i}...")

            # Login sequence (only when credentials are configured)
            guest = settings.guest
            if guest.username:
                logger.info(f"Node {i}: Sending login credentials")
                self.tmux.send_keys(pane_idx, guest.username)
                time.sleep(1)
                if guest.password:
                    self.tmux.send_keys(pane_idx, guest.password, sensitive=True)
                time.sleep(2)  # Wait for shell to be ready

            # Apply configuration
            self._apply_node_config(i, pane_idx)

    def _apply_node_config(self, node_id: int, pane_idx: int):
        """Applies configuration to a single node, in this order:
        1. Enter config mode (if configured)
        2. Load the node config file (if configured)
        3. Execute common/global commands from the user config
        4. Execute scenario-specific commands
        5. Commit and leave config mode (if configured)
        """
        guest = settings.guest

        # Step 1: Enter config mode
        if guest.enter_config_command:
            logger.info(f"Node {node_id}: Entering configuration mode")
            self.tmux.send_keys(pane_idx, guest.enter_config_command)
            time.sleep(1)

        # Step 2: Load device-specific config
        if guest.load_config_command:
            logger.info(f"Node {node_id}: Loading cfg_dut{node_id}")
            self.tmux.send_keys(
                pane_idx, guest.load_config_command.format(file=f"cfg_dut{node_id}")
            )
            time.sleep(2)

        # Step 3: Common commands (global, applies to all scenarios)
        logger.info(f"Node {node_id}: Applying common commands")

        for cmd_obj in settings.get_common_commands():
            logger.info(f"Node {node_id}: {cmd_obj.description or cmd_obj.command}")
            self.tmux.send_keys(pane_idx, cmd_obj.command)
            time.sleep(0.5)
            password = cmd_obj.resolved_password()
            if password:
                self.tmux.send_keys(pane_idx, password, sensitive=True)
                time.sleep(0.5)

        # Step 4: Scenario-specific commands
        if self.ctx.selected_scenario and self.ctx.selected_scenario.config:
            config = self.ctx.selected_scenario.config

            if config.commands:
                logger.info(f"Node {node_id}: Executing scenario commands")
                for cmd_obj in config.commands:
                    logger.info(f"Node {node_id}: {cmd_obj.description or cmd_obj.command}")
                    self.tmux.send_keys(pane_idx, cmd_obj.command)
                    time.sleep(1)

        # Step 5: Commit and exit
        if guest.commit_command:
            logger.info(f"Node {node_id}: Committing configuration")
            self.tmux.send_keys(pane_idx, guest.commit_command)
            time.sleep(2)

        if guest.exit_config_command:
            logger.info(f"Node {node_id}: Exiting configuration mode")
            self.tmux.send_keys(pane_idx, guest.exit_config_command)
            time.sleep(1)

        logger.info(f"Node {node_id} configured successfully.")
