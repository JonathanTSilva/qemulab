"""Sudo password modal dialog."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class PasswordModal(ModalScreen[str]):
    """A modal screen to request Sudo Password."""

    def compose(self) -> ComposeResult:
        """Create the password dialog."""
        with Vertical(id="password-dialog"):
            yield Label("Sudo Password Required", classes="dialog-title")
            yield Label("Enter your password to configure networking:", classes="dialog-content")
            yield Input(password=True, id="password-input")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Authenticate", variant="primary", id="btn-auth")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-auth":
            inp = self.query_one("#password-input", Input)
            self.dismiss(inp.value)
