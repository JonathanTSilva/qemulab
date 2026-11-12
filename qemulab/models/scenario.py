import re
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class Command(BaseModel):
    """Represents a single command execution in the shell."""

    command: str
    description: str = ""


class ScenarioConfig(BaseModel):
    """
    Represents the schema of 'scenario.json'.
    """

    description: str = "No description provided."
    commands: list[Command] = Field(default_factory=list)


class Scenario(BaseModel):
    """
    Represents a full Scenario on disk.
    It combines the metadata (JSON) with the physical configuration files.
    """

    name: str
    path: Path
    config: ScenarioConfig

    @computed_field
    @property
    def dut_files(self) -> dict[int, Path]:
        """
        Scans the scenario directory for cfg_dutX files.
        Returns a dictionary mapping Node ID -> File Path.
        Example: {1: Path(.../cfg_dut1), 2: Path(.../cfg_dut2)}
        """
        if not self.path.exists():
            return {}

        dut_map = {}
        # Regex to strictly match 'cfg_dut' followed by digits
        pattern = re.compile(r"^cfg_dut(\d+)$")

        for item in self.path.iterdir():
            if item.is_file():
                match = pattern.match(item.name)
                if match:
                    node_id = int(match.group(1))
                    dut_map[node_id] = item

        # Return sorted by node ID for consistency
        return dict(sorted(dut_map.items()))

    @property
    def default_node_count(self) -> int:
        """The default number of nodes is the number of config files found."""
        return len(self.dut_files)

    @property
    def available_node_ids(self) -> list[int]:
        """Returns a list of valid node IDs (e.g., [1, 2, 3, 4])."""
        return list(self.dut_files.keys())
