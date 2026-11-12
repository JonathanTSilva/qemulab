import contextlib
import logging
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)

REDACTED = "<redacted>"


class TmuxService:
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.window_name = "nodes"
        self.tmux_bin = shutil.which("tmux")
        # List to store unique Pane IDs (e.g., ['%1', '%2', '%3', '%4'])
        self.pane_ids = []

    def _run(self, cmd: list[str], check: bool = True, sensitive: bool = False) -> str:
        """Run a tmux command. With `sensitive`, arguments never reach logs or exceptions."""
        full_cmd = [self.tmux_bin] + cmd
        try:
            result = subprocess.run(full_cmd, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if sensitive:
                safe_cmd = [self.tmux_bin, cmd[0], REDACTED]
                logger.debug(f"Tmux command failed: {' '.join(safe_cmd)}")
                raise subprocess.CalledProcessError(e.returncode, safe_cmd) from None
            if check:
                logger.debug(f"Tmux command failed: {' '.join(full_cmd)}")
                logger.debug(f"Tmux Stderr: {e.stderr.strip()}")
            raise e

    def create_session(self):
        """Creates session and captures the first Pane ID."""
        self.pane_ids = []  # Reset

        # 1. Kill existing
        if self.session_exists():
            logger.info(f"Killing existing session: {self.session_name}")
            with contextlib.suppress(Exception):
                self._run(["kill-session", "-t", self.session_name], check=False)
            time.sleep(0.5)

        # 2. Create New and Capture First Pane ID
        logger.info(f"Creating session: {self.session_name}")
        # -P -F "#{pane_id}" prints the unique ID of the first pane (e.g. %0)
        cmd = [
            "new-session",
            "-d",
            "-s",
            self.session_name,
            "-n",
            self.window_name,
            "-P",
            "-F",
            "#{pane_id}",
        ]

        first_pane_id = self._run(cmd)
        self.pane_ids.append(first_pane_id)
        logger.info(f"Session created. Pane 0 ID: {first_pane_id}")

        # 3. Setup Options
        self._run(["set-option", "-t", self.session_name, "mouse", "on"])
        self._run(["set-option", "-t", self.session_name, "history-limit", "5000"])

    def session_exists(self) -> bool:
        try:
            self._run(["has-session", "-t", self.session_name])
            return True
        except subprocess.CalledProcessError:
            return False

    def setup_layout(self, node_count: int):
        """Splits window and captures new Pane IDs for every split.
        Ensures we have exactly 'node_count' tracked panes.
        """
        if node_count <= 1:
            return

        time.sleep(0.2)

        try:
            # We currently have self.pane_ids[0] (Top-Left or Full)

            # Split 1: Split Pane 0 Horizontally -> Creates Pane 1 (Right)
            # cmd: split-window -t %0 -h -P -F "#{pane_id}"
            p1 = self._run(["split-window", "-t", self.pane_ids[0], "-h", "-P", "-F", "#{pane_id}"])
            self.pane_ids.append(p1)

            if node_count > 2:
                # Split 2: Split Pane 0 Vertically -> Creates Pane 2 (Bottom-Left)
                p2 = self._run(
                    ["split-window", "-t", self.pane_ids[0], "-v", "-P", "-F", "#{pane_id}"]
                )
                self.pane_ids.append(p2)

                # Split 3: Split Pane 1 (Right) Vertically -> Creates Pane 3 (Bottom-Right)
                # Note: We target the specific ID we captured earlier (p1)
                p3 = self._run(["split-window", "-t", p1, "-v", "-P", "-F", "#{pane_id}"])
                self.pane_ids.append(p3)

            # Re-organize visually
            self._run(["select-layout", "-t", self.session_name, "tiled"])

            logger.info(f"Layout setup complete. Active Panes: {self.pane_ids}")

        except subprocess.CalledProcessError as e:
            logger.warning(f"Tmux layout split failed: {e}")

    def send_keys(self, pane_index: int, command: str, sensitive: bool = False):
        """Sends command to the pane at specific index.

        Set `sensitive=True` for passwords and anything containing them: the contents are
        then logged as `<redacted>` and never appear in error messages.
        """
        if pane_index >= len(self.pane_ids):
            logger.error(
                f"Cannot send to pane {pane_index}: only {len(self.pane_ids)} panes exist."
            )
            return

        target_id = self.pane_ids[pane_index]
        logger.debug(f"Sending to {target_id}: {REDACTED if sensitive else command}")
        self._run(["send-keys", "-t", target_id, command, "C-m"], sensitive=sensitive)

    def clear_history(self, pane_index: int):
        """Drops the scrollback of a pane (used after typing secrets into it)."""
        if pane_index < len(self.pane_ids):
            self._run(["clear-history", "-t", self.pane_ids[pane_index]], check=False)

    def wait_for_text(
        self, pane_index: int, text: str, timeout: int = 60, poll_interval: float = 2.0
    ) -> bool:
        """Polls specific pane ID until text appears.

        Args:
            pane_index: Index of the pane to monitor
            text: Text to search for in pane output
            timeout: Maximum time to wait in seconds
            poll_interval: Time between checks in seconds

        Returns:
            True if text found, False if timeout
        """
        if pane_index >= len(self.pane_ids):
            logger.error(f"Cannot monitor pane {pane_index}: only {len(self.pane_ids)} panes exist")
            return False

        target_id = self.pane_ids[pane_index]
        start = time.time()
        attempt = 0

        logger.debug(f"Waiting for '{text}' in pane {target_id} (timeout: {timeout}s)")

        while time.time() - start < timeout:
            attempt += 1
            try:
                output = self._run(["capture-pane", "-p", "-t", target_id], check=False)

                # Log every 5th attempt to avoid spam
                if attempt % 5 == 0:
                    logger.debug(f"Pane {pane_index} attempt {attempt}: checking for '{text}'")

                if text in output:
                    logger.info(
                        f"Found '{text}' in pane {pane_index} after {time.time() - start:.1f}s"
                    )
                    return True

            except Exception as e:
                logger.warning(f"Error reading pane {pane_index}: {e}")

            time.sleep(poll_interval)

        # On timeout, capture final output for debugging
        try:
            final_output = self._run(["capture-pane", "-p", "-t", target_id], check=False)
            logger.error(
                f"Timeout waiting for '{text}' in pane {pane_index} after {timeout}s. "
                f"Last output:\n{final_output[-500:]}"  # Last 500 chars
            )
        except Exception:
            logger.error(f"Timeout waiting for '{text}' in pane {pane_index} after {timeout}s")

        return False
