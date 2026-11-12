import logging
import re
from pathlib import Path

from qemulab.config.settings import settings
from qemulab.models.scenario import Scenario, ScenarioConfig

logger = logging.getLogger(__name__)


def _template_regex(template: str, board: str) -> re.Pattern[str]:
    """Compile a '{board}-...-{version}' file name template into a regex capturing the version."""
    prefix, _, suffix = template.replace("{board}", board).partition("{version}")
    return re.compile(rf"^{re.escape(prefix)}(.+){re.escape(suffix)}$")


class Scanner:
    """
    Service responsible for discovering boards, images and scenarios on disk.

    Layout, configurable through settings:
    <images_base_path>/<board_dir_template>/<images_subdir>/<kernel_pattern | initrd_pattern>
    """

    @staticmethod
    def scan_boards(images_path: Path) -> list[str]:
        """
        Scans the images directory for folders matching `settings.board_dir_pattern`.
        Returns a sorted list of board names (e.g., ['board1', 'board2']).
        """
        if not images_path.exists():
            logger.warning(f"Images path does not exist: {images_path}")
            return []

        boards = set()
        pattern = re.compile(settings.board_dir_pattern)

        for item in images_path.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    boards.add(match.group("board"))

        return sorted(boards)

    @staticmethod
    def _images_dir(images_path: Path, board: str) -> Path:
        board_dir = settings.board_dir_template.format(board=board)
        return images_path / board_dir / settings.images_subdir

    @staticmethod
    def scan_versions(images_path: Path, board: str) -> list[str]:
        """
        Scans the images folder of a board to find available versions.
        Looks for files matching `settings.kernel_pattern`.
        """
        images_dir = Scanner._images_dir(images_path, board)

        if not images_dir.exists():
            logger.warning(f"Images directory not found: {images_dir}")
            return []

        versions = set()
        pattern = _template_regex(settings.kernel_pattern, board)

        for item in images_dir.iterdir():
            if item.is_file():
                match = pattern.match(item.name)
                if match:
                    versions.add(match.group(1))

        return sorted(versions, reverse=True)

    @staticmethod
    def resolve_image_paths(
        images_path: Path, board: str, version: str
    ) -> tuple[Path | None, Path | None]:
        """
        Locates the exact kernel and initrd files for a given board and version.
        Falls back to generic 'bzImage' / 'rootfs.cpio' names.

        Returns: (kernel_path, initrd_path)
        """
        images_dir = Scanner._images_dir(images_path, board)
        if not images_dir.exists():
            return None, None

        kernel_candidates = [
            images_dir / settings.kernel_pattern.format(board=board, version=version),
            images_dir / "bzImage",
        ]
        kernel = next((p for p in kernel_candidates if p.exists()), None)

        initrd_candidates = [
            images_dir / settings.initrd_pattern.format(board=board, version=version),
            images_dir / "rootfs.cpio",
        ]
        initrd = next((p for p in initrd_candidates if p.exists()), None)

        return kernel, initrd

    @staticmethod
    def scan_scenarios(scenarios_base_path: Path) -> list[Scenario]:
        """
        Traverses the scenarios directory to build Scenario objects.
        Ignores folders without a 'scenario.json' or valid 'cfg_dut' files.
        """
        results = []

        if not scenarios_base_path.exists():
            logger.warning(f"Scenarios path not found: {scenarios_base_path}")
            return []

        for folder in sorted(scenarios_base_path.iterdir()):
            if not folder.is_dir():
                continue

            json_path = folder / "scenario.json"
            if not json_path.exists():
                # Skip folders that aren't scenarios (e.g. docs, drafts)
                continue

            try:
                # 1. Parse JSON
                with open(json_path) as f:
                    # Helper: Pydantic handles parsing from raw dict
                    # We assume the file contains valid JSON
                    import json

                    data = json.load(f)
                    config = ScenarioConfig(**data)

                # 2. Create Scenario Object (automatically finds cfg_dut files)
                scenario = Scenario(name=folder.name, path=folder, config=config)

                # 3. Only add if it has actual DUT configs or explicitly allows empty
                if scenario.default_node_count > 0:
                    results.append(scenario)

            except Exception as e:
                logger.error(f"Failed to load scenario '{folder.name}': {e}")
                continue

        return results
