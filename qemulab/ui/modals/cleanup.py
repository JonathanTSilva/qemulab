"""Cleanup confirmation modal dialog."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class CleanupModal(ModalScreen[bool]):
    """A modal screen to confirm cleanup before exit."""

    BINDINGS = [
        Binding("left", "focus_previous", show=False),
        Binding("right", "focus_next", show=False),
        Binding("escape", "dismiss_no", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Create the cleanup confirmation dialog."""
        with Vertical(id="cleanup-dialog"):
            yield Label("Cleanup Confirmation", classes="dialog-title")
            yield Static(
                "QEMU environment is running.\n\n"
                "Clean up before exit?\n"
                "• Kill QEMU instances\n"
                "• Remove network interfaces\n"
                "• Delete flash directories\n"
                "• Terminate tmux session",
                classes="dialog-content",
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Yes, Cleanup", variant="primary", id="btn-yes")
                yield Button("No, Keep Running", variant="default", id="btn-no")

    def on_mount(self) -> None:
        """Focus the first button when modal opens."""
        self.query_one("#btn-yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-yes":
            self.dismiss(True)
        elif event.button.id == "btn-no":
            self.dismiss(False)

    def action_dismiss_no(self) -> None:
        """Handle escape key - same as No."""
        self.dismiss(False)
