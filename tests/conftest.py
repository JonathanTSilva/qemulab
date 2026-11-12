"""Pytest configuration and shared fixtures."""

import logging
import sys
import warnings
from io import StringIO

import pytest


@pytest.fixture(autouse=True)
def isolate_user_config(tmp_path, monkeypatch):
    """Never read the developer's real ~/.config/qemulab/config.yaml during tests."""
    monkeypatch.setenv("QEMULAB_CONFIG", str(tmp_path / "no-user-config.yaml"))


@pytest.fixture(autouse=True)
def suppress_all_output(caplog, monkeypatch):
    """Suppress all logging and print statements during tests.
    This prevents application logs from polluting test output.
    """
    # 1. Suppress all qemulab loggers
    for name in list(logging.root.manager.loggerDict.keys()):
        if name.startswith("qemulab") or name == "asyncio":
            logger = logging.getLogger(name)
            logger.setLevel(logging.CRITICAL + 1)  # Above CRITICAL
            logger.propagate = False

    # 2. Set caplog to only capture CRITICAL+ (nothing will reach this)
    caplog.set_level(logging.CRITICAL + 1)

    # 3. Suppress asyncio debug messages
    logging.getLogger("asyncio").setLevel(logging.CRITICAL + 1)

    # 4. Capture any stray prints
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    # 5. Suppress warnings
    warnings.filterwarnings("ignore")

    yield

    # Cleanup: restore everything
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    for name in list(logging.root.manager.loggerDict.keys()):
        if name.startswith("qemulab") or name == "asyncio":
            logger = logging.getLogger(name)
            logger.setLevel(logging.NOTSET)
            logger.propagate = True


@pytest.fixture
def enable_logging():
    """Fixture to explicitly enable logging for specific tests that need it."""
    logging.disable(logging.NOTSET)
    yield
    logging.disable(logging.CRITICAL)


@pytest.fixture
def temp_scenario_dir(tmp_path):
    """Creates a temporary scenario directory with test files."""
    scenario_dir = tmp_path / "test_scenario"
    scenario_dir.mkdir()

    # Create dummy config files
    for i in range(1, 5):
        cfg_file = scenario_dir / f"cfg_dut{i}"
        cfg_file.write_text(f"test config for node {i}\n")

    # Create scenario.json
    scenario_json = scenario_dir / "scenario.json"
    scenario_json.write_text('{"description": "Test scenario"}')

    return scenario_dir


@pytest.fixture
def mock_images_structure(tmp_path):
    """Creates a mock images_root directory structure."""
    images_root = tmp_path / "images_root"
    images_root.mkdir()

    # Create board directory
    board_dir = images_root / "board1"
    images_dir = board_dir / "images"
    images_dir.mkdir(parents=True)

    # Create dummy kernel and initrd
    (images_dir / "board1-bzImage-1.0.0").touch()
    (images_dir / "board1-rootfs.cpio-1.0.0").touch()

    return images_root
