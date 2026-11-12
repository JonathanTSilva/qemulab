from pathlib import Path

from pydantic import BaseModel, PrivateAttr

from qemulab.models.scenario import Scenario


class SessionContext(BaseModel):
    """
    Holds the runtime selection state of the user.
    """

    selected_board: str
    selected_version: str | None = None

    # The currently selected Scenario object (includes path, config, and file list)
    selected_scenario: Scenario | None = None

    image_path: Path | None = None
    kernel_path: Path | None = None
    initrd_path: Path | None = None
    sudo_password: str | None = None

    # Internal override if the user manually changes the count in the UI
    _manual_node_count: int | None = PrivateAttr(default=None)

    @property
    def node_count(self) -> int:
        """
        Returns the effective number of nodes to launch.
        1. If user manually overrode it (e.g., changed 4 to 2), return that.
        2. If a scenario is selected, return its file count.
        3. Otherwise, return 0.
        """
        if self._manual_node_count is not None:
            return self._manual_node_count
        if self.selected_scenario:
            return self.selected_scenario.default_node_count
        return 0

    def set_manual_node_count(self, count: int):
        """Allows the UI to override the default count."""
        # Validation could go here (e.g. check against max_nodes_limit)
        self._manual_node_count = count

    def reset_node_count(self):
        """Resets the count to follow the scenario default."""
        self._manual_node_count = None
