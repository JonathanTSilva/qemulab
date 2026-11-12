import json
import logging
from pathlib import Path

import pytest

from qemulab.services.scanner import Scanner


@pytest.fixture(autouse=True)
def silence_scanner_logger():
    """
    Suppress ERROR logs from Scanner during tests (e.g. broken JSON tests).
    """
    logger = logging.getLogger("qemulab.services.scanner")
    previous_level = logger.level

    # Set to CRITICAL to hide the "Failed to load scenario..." ERROR logs
    logger.setLevel(logging.CRITICAL)

    yield

    # Restore original level
    logger.setLevel(previous_level)


@pytest.fixture
def mock_images(tmp_path):
    """Creates a fake images_root structure."""
    root = tmp_path / "images_root"
    root.mkdir()

    # Board 1: board1 (Valid)
    b1 = root / "board1" / "images"
    b1.mkdir(parents=True)
    (b1 / "board1-bzImage-1.0.0").touch()
    (b1 / "board1-rootfs.cpio-1.0.0").touch()

    # Board 2: board2 (No images)
    b2 = root / "board2" / "images"
    b2.mkdir(parents=True)

    # Invalid Folder (Should be ignored)
    (root / "not-a-board").mkdir()

    return root


@pytest.fixture
def mock_scenarios(tmp_path):
    """Creates a fake scenario library."""
    root = tmp_path / "scenarios"
    root.mkdir()

    # Scenario A: Valid
    scen_a = root / "ospf_test"
    scen_a.mkdir()
    (scen_a / "cfg_dut1").touch()
    (scen_a / "cfg_dut2").touch()

    config_a = {"description": "OSPF Test", "commands": []}
    with open(scen_a / "scenario.json", "w") as f:
        json.dump(config_a, f)

    # Scenario B: Missing JSON (Should be ignored)
    scen_b = root / "draft_test"
    scen_b.mkdir()
    (scen_b / "cfg_dut1").touch()

    # Scenario C: Invalid JSON (Should be handled gracefully)
    scen_c = root / "broken_json"
    scen_c.mkdir()
    with open(scen_c / "scenario.json", "w") as f:
        f.write("{ invalid_json }")

    return root


def test_scan_boards(mock_images):
    """Test discovery of board folders."""
    boards = Scanner.scan_boards(mock_images)
    assert "board1" in boards
    assert "board2" in boards
    assert len(boards) == 2  # 'invalid_folder' should be ignored


def test_scan_versions(mock_images):
    """Test parsing of version strings from filenames."""
    versions = Scanner.scan_versions(mock_images, "board1")
    assert "1.0.0" in versions
    assert len(versions) == 1


def test_resolve_image_paths(mock_images):
    """Test that scanner finds the matching kernel and initrd pair."""
    kernel, initrd = Scanner.resolve_image_paths(mock_images, "board1", "1.0.0")

    assert kernel is not None
    assert initrd is not None
    assert kernel.name == "board1-bzImage-1.0.0"
    assert initrd.name == "board1-rootfs.cpio-1.0.0"


def test_resolve_image_paths_missing(mock_images):
    """Test handling of non-existent versions."""
    kernel, initrd = Scanner.resolve_image_paths(mock_images, "board1", "99.9.9")
    assert kernel is None
    # Depending on logic, initrd might be None or fallback to rootfs.cpio if it exists
    # In our mock, generic rootfs doesn't exist, so both should be None
    assert initrd is None


def test_scan_scenarios(mock_scenarios):
    """Test loading valid scenarios and ignoring invalid ones."""
    results = Scanner.scan_scenarios(mock_scenarios)

    # Should only find 'ospf_test'
    # 'draft_test' has no json -> ignored
    # 'broken_json' fails parsing -> ignored/logged
    assert len(results) == 1
    scenario = results[0]

    assert scenario.name == "ospf_test"
    assert scenario.default_node_count == 2
    assert scenario.config.description == "OSPF Test"


def test_example_scenario_is_valid():
    """The bundled example scenario loads and has two nodes."""
    repo_scenarios = Path(__file__).parent.parent.parent / "scenarios"
    results = Scanner.scan_scenarios(repo_scenarios)
    assert [s.name for s in results] == ["two-router-link"]
    assert results[0].default_node_count == 2


def test_custom_image_patterns(tmp_path, monkeypatch):
    """Board directory and image file name patterns are configurable."""
    from qemulab.services import scanner

    images = tmp_path / "root" / "out_alpha" / "img"
    images.mkdir(parents=True)
    (images / "kernel-alpha_2.1").touch()
    (images / "initrd-alpha_2.1").touch()
    monkeypatch.setattr(scanner.settings, "board_dir_pattern", r"^out_(?P<board>\w+)$")
    monkeypatch.setattr(scanner.settings, "board_dir_template", "out_{board}")
    monkeypatch.setattr(scanner.settings, "images_subdir", "img")
    monkeypatch.setattr(scanner.settings, "kernel_pattern", "kernel-{board}_{version}")
    monkeypatch.setattr(scanner.settings, "initrd_pattern", "initrd-{board}_{version}")

    root = tmp_path / "root"
    assert Scanner.scan_boards(root) == ["alpha"]
    assert Scanner.scan_versions(root, "alpha") == ["2.1"]
    kernel, initrd = Scanner.resolve_image_paths(root, "alpha", "2.1")
    assert kernel is not None
    assert kernel.name == "kernel-alpha_2.1"
    assert initrd is not None
    assert initrd.name == "initrd-alpha_2.1"
