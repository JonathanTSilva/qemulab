"""Running environment screen."""

import logging
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, LoadingIndicator, RichLog, Static


class RunningScreen(Vertical):
    """Screen displayed when environment is running."""

    def __init__(self, *, id: str = "running-screen") -> None:
        super().__init__(id=id)
        self.logs_visible = False

    def compose(self) -> ComposeResult:
        """Create the running screen layout."""
        yield Label("Environment Status", classes="page-header")

        with Vertical(id="status-container"):
            yield LoadingIndicator(id="loading-spinner")
            yield Static(
                "Press 'L' to show/hide logs • Press 'S' to save logs to file",
                id="log-hint",
                classes="log-hint",
            )
            yield RichLog(id="log-view", markup=True)

    def on_mount(self) -> None:
        """Initialize the running screen."""
        # Initially hide the log view
        log_view = self.query_one("#log-view", RichLog)
        log_view.display = False

    def setup_logging(self) -> None:
        """Setup logging to display in the RichLog widget."""
        log_view = self.query_one("#log-view", RichLog)

        # Create a custom handler that writes to RichLog
        handler = TextualHandler(log_view)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def toggle_logs(self) -> None:
        """Toggle visibility of logs."""
        log_view = self.query_one("#log-view", RichLog)
        self.logs_visible = not self.logs_visible
        log_view.display = self.logs_visible

        # Update hint text
        hint = self.query_one("#log-hint", Static)
        if self.logs_visible:
            hint.update("Press 'L' to hide logs • Press 'S' to save logs to file")
        else:
            hint.update("Press 'L' to show logs • Press 'S' to save logs to file")

    def show_logs(self) -> None:
        """Show the logs panel."""
        log_view = self.query_one("#log-view", RichLog)
        log_view.display = True
        self.logs_visible = True

        hint = self.query_one("#log-hint", Static)
        hint.update("✓ Environment Ready! • Press 'L' to hide logs • Press 'S' to save logs")

    def hide_spinner(self) -> None:
        """Hide the loading spinner."""
        spinner = self.query_one("#loading-spinner", LoadingIndicator)
        spinner.display = False

    def save_logs(self) -> tuple[bool, str]:
        """Save logs to a file.

        Returns:
            Tuple of (success, message)
        """
        try:
            log_view = self.query_one("#log-view", RichLog)

            # Extract lines from RichLog
            lines = []
            for line in log_view._lines:
                if hasattr(line, "plain"):
                    lines.append(line.plain)
                else:
                    lines.append(str(line))

            log_content = "\n".join(lines)

            # Save to current directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"qemulab_session_{timestamp}.log"
            log_path = Path.cwd() / log_filename

            log_path.write_text(log_content)

            return True, f"Logs saved to {log_path}"
        except Exception as e:
            return False, f"Failed to save logs: {e}"


class TextualHandler(logging.Handler):
    """Logging handler that writes to a Textual RichLog widget."""

    def __init__(self, widget: RichLog) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the widget."""
        try:
            msg = self.format(record)
            self.widget.write(msg)
        except Exception:
            pass
