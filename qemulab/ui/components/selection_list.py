"""Reusable selection list component."""

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView


class ItemSelected(Message):
    """Message posted when an item is selected from the list."""

    def __init__(self, list_id: str, index: int, item: Any) -> None:
        super().__init__()
        self.list_id = list_id
        self.index = index
        self.item = item


class SelectionList(Vertical):
    """A styled list view with a header for item selection."""

    def __init__(
        self,
        title: str,
        list_id: str,
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.title = title
        self.list_id = list_id
        self._items: list[Any] = []

    def compose(self) -> ComposeResult:
        """Create the list with header."""
        yield Label(self.title, classes="page-header")
        yield ListView(id=self.list_id)

    def load_items(self, items: list[Any], formatter: Callable[[Any], str] | None = None) -> None:
        """Load items into the list.

        Args:
            items: List of items to display
            formatter: Optional function to format items as strings
        """
        self._items = items
        list_view = self.query_one(f"#{self.list_id}", ListView)
        list_view.clear()

        for item in items:
            display_text = formatter(item) if formatter else str(item)
            list_view.append(ListItem(Label(display_text)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection and post message."""
        if event.list_view.id == self.list_id:
            self.post_message(
                ItemSelected(
                    self.list_id, event.list_view.index, self._items[event.list_view.index]
                )
            )
