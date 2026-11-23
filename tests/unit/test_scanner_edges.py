"""Scanner edge cases: missing directories, unmatched kernels, generic fallbacks."""

from pathlib import Path

from qemulab.config.settings import settings
from qemulab.services.scanner import Scanner


def test_scan_boards_missing_root(tmp_path):
    assert Scanner.scan_boards(tmp_path / "nope") == []


def test_scan_boards_ignores_files_and_non_matching_dirs(tmp_path):
    (tmp_path / "board1").mkdir()
    (tmp_path / "bad-name").mkdir()
    (tmp_path / "file.txt").write_text("x")
    assert Scanner.scan_boards(tmp_path) == ["board1"]


def test_scan_versions_missing_images_dir(tmp_path):
    assert Scanner.scan_versions(tmp_path, "board1") == []


def test_scan_versions_skips_dirs_and_unmatched_files(tmp_path):
    images = tmp_path / "board1" / settings.images_subdir
    images.mkdir(parents=True)
    (images / "board1-bzImage-1.0").touch()
    (images / "unrelated.txt").touch()
    (images / "board1-bzImage-2.0").mkdir()
    assert Scanner.scan_versions(tmp_path, "board1") == ["1.0"]


def test_resolve_image_paths_missing_dir(tmp_path):
    assert Scanner.resolve_image_paths(tmp_path, "board1", "1.0") == (None, None)


def test_resolve_image_paths_generic_fallback(tmp_path):
    images = tmp_path / "board1" / settings.images_subdir
    images.mkdir(parents=True)
    (images / "bzImage").touch()
    (images / "rootfs.cpio").touch()
    kernel, initrd = Scanner.resolve_image_paths(tmp_path, "board1", "9.9")
    assert kernel == images / "bzImage"
    assert initrd == images / "rootfs.cpio"


def test_resolve_image_paths_nothing_found(tmp_path):
    images = tmp_path / "board1" / settings.images_subdir
    images.mkdir(parents=True)
    assert Scanner.resolve_image_paths(tmp_path, "board1", "1.0") == (None, None)


def test_scan_scenarios_missing_root(tmp_path):
    assert Scanner.scan_scenarios(Path(tmp_path / "nope")) == []


def test_scan_scenarios_skips_plain_files(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    assert Scanner.scan_scenarios(tmp_path) == []
