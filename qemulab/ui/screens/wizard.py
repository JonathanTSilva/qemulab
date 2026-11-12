"""Wizard screen for environment setup."""

import contextlib

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Label, Static

from qemulab.config.settings import settings
from qemulab.models.context import SessionContext
from qemulab.models.scenario import Scenario
from qemulab.services.scanner import Scanner
from qemulab.ui.components import ItemSelected, SelectionList, StepClicked, StepIndicator


class SummaryItem(Static):
    """Display a Key: Value pair as a single formatted line."""

    def __init__(self, label: str, value: str) -> None:
        content = f"[bold cyan]{label}:[/bold cyan] {value}"
        super().__init__(content)


class WizardScreen(Vertical):
    """Main wizard screen for configuring the QEMU environment."""

    STEPS = ["Board", "Version", "Scenario", "Node Count", "Confirmation"]

    def __init__(
        self,
        context: SessionContext,
        *,
        id: str = "wizard-screen",
    ) -> None:
        super().__init__(id=id)
        self.ctx = context
        self.boards: list[str] = []
        self.versions: list[str] = []
        self.scenarios: list[Scenario] = []
        self.current_step_idx = 0

    def compose(self) -> ComposeResult:
        """Create the wizard layout."""
        with Container(id="wizard-grid"):
            # Sidebar with wizard steps
            with Vertical(id="sidebar"):
                yield Label("WIZARD STEPS", id="sidebar-header")
                for i, step in enumerate(self.STEPS):
                    yield StepIndicator(i, step, id=f"step-{i}")

            # Content area with all wizard pages
            with ContentSwitcher(initial="page-board", id="content-area"):
                # Board selection
                yield SelectionList("Select Board", "list-board", id="page-board")

                # Version selection
                yield SelectionList("Select Firmware Version", "list-version", id="page-version")

                # Scenario selection
                yield SelectionList("Select Test Scenario", "list-scenario", id="page-scenario")

                # Node count selection
                yield SelectionList(
                    "Select Number of Nodes", "list-node-count", id="page-node-count"
                )

                # Confirmation page
                with Vertical(id="page-confirm"):
                    yield Label("Summary & Launch", classes="page-header")
                    with Vertical(id="summary-container"):
                        yield Container(id="summary-card", classes="summary-card")
                    with Horizontal():
                        yield Button("LAUNCH ENVIRONMENT", variant="primary", id="btn-launch")

    def on_mount(self) -> None:
        """Initialize the wizard when mounted."""
        self.load_boards()

    # --- Data Loading Methods ---

    def load_boards(self) -> None:
        """Load available boards."""
        self.boards = Scanner.scan_boards(settings.images_base_path)
        page = self.query_one("#page-board", SelectionList)
        page.load_items(self.boards)
        self.switch_to_step(0)

    def load_versions(self) -> None:
        """Load available image versions for the selected board."""
        self.versions = Scanner.scan_versions(settings.images_base_path, self.ctx.selected_board)
        page = self.query_one("#page-version", SelectionList)
        page.load_items(self.versions)
        self.switch_to_step(1)

    def load_scenarios(self) -> None:
        """Load available test scenarios."""
        scenarios_path = settings.scenarios_path
        self.scenarios = Scanner.scan_scenarios(scenarios_path)
        page = self.query_one("#page-scenario", SelectionList)
        page.load_items(
            self.scenarios, formatter=lambda s: f"{s.name} ({s.default_node_count} nodes)"
        )
        self.switch_to_step(2)

    def load_node_count_options(self) -> None:
        """Load node count options based on selected scenario."""
        if not self.ctx.selected_scenario:
            return

        max_nodes = self.ctx.selected_scenario.default_node_count
        node_options = [f"{i} node" if i == 1 else f"{i} nodes" for i in range(1, max_nodes + 1)]

        page = self.query_one("#page-node-count", SelectionList)
        page.load_items(node_options)
        self.switch_to_step(3)

    def load_summary(self) -> None:
        """Load the summary/confirmation page."""
        card = self.query_one("#summary-card", Container)
        card.remove_children()

        items = [
            ("Board", self.ctx.selected_board),
            ("Version", self.ctx.selected_version or "N/A"),
            ("Scenario", self.ctx.selected_scenario.name if self.ctx.selected_scenario else "N/A"),
            ("Nodes", str(self.ctx.node_count)),
            ("Kernel", self.ctx.kernel_path.name if self.ctx.kernel_path else "N/A"),
        ]

        for key, value in items:
            card.mount(SummaryItem(key, value))

        self.switch_to_step(4)

    # --- Navigation Methods ---

    def switch_to_step(self, idx: int) -> None:
        """Switch to a specific wizard step."""
        self.current_step_idx = idx

        # Update step indicators
        for i in range(len(self.STEPS)):
            step_widget = self.query_one(f"#step-{i}", StepIndicator)
            if i < idx:
                step_widget.state = "completed"
            elif i == idx:
                step_widget.state = "active"
            else:
                step_widget.state = "pending"

        # Switch content page
        pages = [
            "page-board",
            "page-version",
            "page-scenario",
            "page-node-count",
            "page-confirm",
        ]
        self.query_one("#content-area", ContentSwitcher).current = pages[idx]

        # Set focus
        if idx < 4:
            page_id = pages[idx]
            with contextlib.suppress(Exception):
                self.query_one(f"#{page_id}").focus()
        elif idx == 4:
            self.query_one("#btn-launch").focus()

    def can_go_back(self) -> bool:
        """Check if we can navigate backwards."""
        return self.current_step_idx > 0

    def go_back(self) -> None:
        """Navigate to the previous step."""
        if self.can_go_back():
            self.switch_to_step(self.current_step_idx - 1)

    # --- Event Handlers ---

    def on_step_clicked(self, event: StepClicked) -> None:
        """Handle wizard step clicks for navigation."""
        if event.step_index <= self.current_step_idx:
            self.switch_to_step(event.step_index)

    def on_item_selected(self, event: ItemSelected) -> None:
        """Handle item selection from lists."""
        if event.list_id == "list-board":
            self.ctx.selected_board = self.boards[event.index]
            self.load_versions()

        elif event.list_id == "list-version":
            self.ctx.selected_version = self.versions[event.index]
            kernel, initrd = Scanner.resolve_image_paths(
                settings.images_base_path, self.ctx.selected_board, self.ctx.selected_version
            )
            if not kernel:
                # Post error message to app
                self.app.notify("Kernel not found!", severity="error")
                return
            self.ctx.kernel_path = kernel
            self.ctx.initrd_path = initrd
            self.load_scenarios()

        elif event.list_id == "list-scenario":
            self.ctx.selected_scenario = self.scenarios[event.index]
            self.ctx.reset_node_count()
            self.load_node_count_options()

        elif event.list_id == "list-node-count":
            selected_count = event.index + 1
            self.ctx.set_manual_node_count(selected_count)
            self.load_summary()
