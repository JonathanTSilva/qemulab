"""Wizard step indicator component."""

from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget


class StepClicked(Message):
    """Message posted when a wizard step is clicked."""

    def __init__(self, step_index: int) -> None:
        super().__init__()
        self.step_index = step_index


class StepIndicator(Widget):
    """A single step in the wizard sidebar."""

    label = reactive("")
    state = reactive("pending")
    can_focus = True

    def __init__(self, step_index: int, label: str, id: str) -> None:
        super().__init__(id=id)
        self.step_index = step_index
        self.label = label

    def render(self) -> str:
        """Render the step with appropriate icon."""
        icon = "○"
        if self.state == "active":
            icon = "●"
        elif self.state == "completed":
            icon = "✓"

        return f"{self.step_index + 1}. {self.label}  {icon}"

    def watch_state(self, new_state: str) -> None:
        """Update CSS classes when state changes."""
        self.remove_class("pending", "active", "completed")
        self.add_class(new_state)

    async def on_click(self) -> None:
        """Handle click event on wizard step."""
        # Only allow clicking on completed or active steps
        if self.state in ("completed", "active"):
            self.post_message(StepClicked(self.step_index))
