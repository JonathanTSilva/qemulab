"""Status panel component for displaying environment status."""

from textual.reactive import reactive
from textual.widgets import Static


class StatusPanel(Static):
    """Component that displays the current environment status."""

    status = reactive("stopped")

    def __init__(self, id: str = "status-indicator") -> None:
        super().__init__("", id=id)

    def watch_status(self, new_status: str) -> None:
        """Update the status display when status changes."""
        self.remove_class("status-stopped", "status-starting", "status-running")
        self.add_class(f"status-{new_status}")

        if new_status == "stopped":
            self.update("● [dim]Environment: Stopped[/dim]")
        elif new_status == "starting":
            self.update("● [yellow]Environment: Starting...[/yellow]")
        elif new_status == "running":
            self.update("● [green]Environment: Running[/green]")
