"""Main QemuLab TUI application."""

import logging
import subprocess
import time

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, ContentSwitcher, Footer, Header

from qemulab.config.settings import settings
from qemulab.models.context import SessionContext
from qemulab.services.engine import Engine
from qemulab.ui.components import StatusPanel
from qemulab.ui.modals import CleanupModal, PasswordModal
from qemulab.ui.screens import RunningScreen, WizardScreen
from qemulab.utils.paths import flash_dir_for, remove_tree


class QemuLabApp(App):
    """Main application for QemuLab TUI."""

    CSS_PATH = "app.tcss"
    TITLE = "QemuLab Manager"

    # Reactive property for environment status
    env_status = reactive("stopped")

    BINDINGS = [
        Binding("q", "request_quit", "Quit", priority=True),
        Binding("ctrl+c", "request_quit", "Quit", priority=True),
        Binding("b", "step_back", "Back"),
        Binding("l", "toggle_logs", "Toggle Logs"),
        Binding("s", "save_logs", "Save Logs", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.ctx = SessionContext(selected_board="")
        self.cleanup_performed = False
        self.engine: Engine | None = None
        self._wizard_screen: WizardScreen | None = None
        self._running_screen: RunningScreen | None = None

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header()

        with Container(id="app-grid"):
            # Status bar at the top
            with Horizontal(id="status-bar"):
                yield StatusPanel()

            # Content switcher for wizard and running screens
            with ContentSwitcher(initial="wizard-content", id="main-content"):
                yield Vertical(id="wizard-content")
                yield Vertical(id="running-content")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        # Create and mount wizard screen
        self._wizard_screen = WizardScreen(self.ctx)
        wizard_container = self.query_one("#wizard-content", Vertical)
        wizard_container.mount(self._wizard_screen)

        # Create and mount running screen
        self._running_screen = RunningScreen()
        running_container = self.query_one("#running-content", Vertical)
        running_container.mount(self._running_screen)
        self._running_screen.setup_logging()

        # Update status indicator
        self._update_status()

    def watch_env_status(self, new_status: str) -> None:
        """Called when env_status changes."""
        self._update_status()

    def _update_status(self) -> None:
        """Update the status indicator based on environment state."""
        status_panel = self.query_one(StatusPanel)
        status_panel.status = self.env_status

    # --- Navigation Actions ---

    def action_step_back(self) -> None:
        """Navigate back in the wizard."""
        if self._wizard_screen and self._wizard_screen.can_go_back():
            # Only allow back navigation when on wizard screen
            current = self.query_one("#main-content", ContentSwitcher).current
            if current == "wizard-content":
                self._wizard_screen.go_back()

    def action_toggle_logs(self) -> None:
        """Toggle visibility of logs on the running page."""
        current = self.query_one("#main-content", ContentSwitcher).current
        if current == "running-content" and self._running_screen:
            self._running_screen.toggle_logs()

    def action_save_logs(self) -> None:
        """Save logs to a file."""
        current = self.query_one("#main-content", ContentSwitcher).current
        if current == "running-content" and self._running_screen:
            success, message = self._running_screen.save_logs()
            severity = "success" if success else "error"
            self.notify(message, severity=severity, timeout=5)

    def action_request_quit(self) -> None:
        """Handle quit request with cleanup."""
        current = self.query_one("#main-content", ContentSwitcher).current

        # If environment is running, show confirmation dialog
        if current == "running-content" and self.engine is not None:
            self.push_screen(CleanupModal(), self.handle_cleanup_response)
        else:
            # No environment running, quit immediately
            self.exit()

    def handle_cleanup_response(self, should_cleanup: bool) -> None:
        """Handle user's response to cleanup confirmation."""
        if should_cleanup:
            self.perform_cleanup()
            self.env_status = "stopped"
        self.exit()

    # --- Launch Flow ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses throughout the app."""
        if event.button.id == "btn-launch":
            self.check_sudo_and_launch()

    def check_sudo_and_launch(self) -> None:
        """Prompt for sudo password before launch."""
        self.push_screen(PasswordModal(), self.on_password_entered)

    def on_password_entered(self, password: str) -> None:
        """Handle password entry and start launch."""
        if not password:
            self.notify("Launch aborted.", severity="warning")
            return

        try:
            # Validate password
            subprocess.run(
                ["sudo", "-S", "-v"],
                input=password + "\n",
                text=True,
                capture_output=True,
                check=True,
            )
            # Save password to context
            self.ctx.sudo_password = password

            self.notify("Sudo authenticated!", severity="success")
            self.start_launch_sequence()
        except subprocess.CalledProcessError:
            self.notify("Incorrect password. Sudo failed.", severity="error")

    def start_launch_sequence(self) -> None:
        """Start the environment launch sequence."""
        self.env_status = "starting"

        # Switch to running screen
        self.query_one("#main-content", ContentSwitcher).current = "running-content"

        # Start the engine in a worker thread
        self.run_worker(self._engine_worker, thread=True)

    def _engine_worker(self) -> None:
        """Worker that runs the engine setup."""
        try:
            logging.info("Initializing Engine...")
            self.engine = Engine(self.ctx)

            logging.info("Preparing Environment...")
            self.engine.prepare_environment()

            logging.info("Starting QEMU/Tmux Session...")
            self.engine.start()

            logging.info("Waiting for Nodes (Smart Polling)...")
            self.engine.configure_nodes()

            self.call_from_thread(self._on_launch_success, settings.tmux_session_name)
        except Exception as e:
            error_msg = str(e)
            logging.exception(f"Engine Failure: {error_msg}")
            safe_msg = escape(error_msg)
            self.call_from_thread(
                self.notify, f"Error: {safe_msg}", severity="error", timeout=10, markup=False
            )

    def _on_launch_success(self, session_name: str) -> None:
        """Called when environment launch succeeds."""
        if self._running_screen:
            self._running_screen.hide_spinner()
            self._running_screen.show_logs()

        # Update environment status to running
        self.env_status = "running"

        self.notify("Scenario Launched!", severity="success")
        logging.info("=" * 60)
        logging.info("SUCCESS! Environment is ready.")
        logging.info(f"Attach to tmux: tmux attach -t {session_name}")
        logging.info("=" * 60)

    # --- Cleanup ---

    def perform_cleanup(self) -> None:
        """Perform full cleanup of all resources."""
        if self.cleanup_performed:
            return

        self.cleanup_performed = True

        try:
            logging.info("=" * 60)
            logging.info("Starting cleanup process...")
            logging.info("=" * 60)

            self.notify("Cleaning up environment...", severity="warning", timeout=3)

            def sudo_run(cmd: list[str]) -> None:
                """Run command with sudo using cached password."""
                if self.ctx.sudo_password:
                    proc = subprocess.Popen(
                        ["sudo", "-S"] + cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    proc.communicate(input=f"{self.ctx.sudo_password}\n".encode())
                    proc.wait()
                else:
                    subprocess.run(
                        ["sudo"] + cmd,
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        check=False,
                    )

            # 1. Stop QEMU processes gracefully
            if self.engine and self.engine.tmux:
                logging.info("Stopping QEMU instances...")
                try:
                    for i in range(self.ctx.node_count):
                        try:
                            self.engine.tmux.send_keys(i, "\x02x")
                        except Exception as e:
                            logging.debug(f"Error sending shutdown to pane {i}: {e}")
                    time.sleep(2)
                except Exception as e:
                    logging.warning(f"Error during QEMU shutdown: {e}")

            # 2. Kill tmux session
            logging.info("Terminating tmux session...")
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", settings.tmux_session_name],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    check=False,
                )
            except Exception as e:
                logging.warning(f"Error killing tmux session: {e}")

            # 3. Kill any remaining QEMU processes
            logging.info("Killing remaining QEMU processes...")
            try:
                sudo_run(["pkill", "-f", f"QEMU_{self.ctx.selected_board}"])
            except Exception as e:
                logging.warning(f"Error killing QEMU processes: {e}")

            # 4. Cleanup network interfaces
            logging.info("Removing network interfaces...")
            try:
                for i in range(1, self.ctx.node_count + 1):
                    sudo_run(["ip", "link", "delete", f"tap_qlab{i}_0"])
                    sudo_run(["ip", "link", "delete", f"tap_qlab{i}_1"])

                sudo_run(["ip", "link", "delete", settings.network.mgmt.bridge_name])
                sudo_run(["ip", "link", "delete", settings.network.data_bridge_name])
            except Exception as e:
                logging.warning(f"Error during network cleanup: {e}")

            # 5. Cleanup flash directories
            logging.info("Removing flash directories...")
            for i in range(1, self.ctx.node_count + 1):
                flash_dir = flash_dir_for(i, settings.flash_base_path)
                try:
                    if flash_dir.exists():
                        remove_tree(flash_dir, lambda p: sudo_run(["rm", "-rf", str(p)]))
                        logging.info(f"Removed {flash_dir}")
                except Exception as e:
                    logging.warning(f"Error removing {flash_dir}: {e}")

            logging.info("=" * 60)
            logging.info("Cleanup completed successfully!")
            logging.info("=" * 60)

            self.notify("Cleanup complete!", severity="success", timeout=2)

        except Exception as e:
            logging.exception(f"Error during cleanup: {e}")
            self.notify(f"Cleanup error: {e}", severity="error", timeout=3)
