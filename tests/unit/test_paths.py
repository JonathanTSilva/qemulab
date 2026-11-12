"""Tests for private working dirs and the sudo safety checks."""

import os
from unittest.mock import MagicMock, patch

import pytest

from qemulab.utils import paths
from qemulab.utils.paths import (
    UnsafePathError,
    ensure_private_dir,
    flash_dir_for,
    remove_tree,
    runtime_base_dir,
    verify_safe_for_sudo,
)


def test_verify_accepts_plain_user_owned_dir(tmp_path):
    d = tmp_path / "a" / "b"
    d.mkdir(parents=True)
    assert verify_safe_for_sudo(d) == d


def test_verify_accepts_missing_path(tmp_path):
    assert verify_safe_for_sudo(tmp_path / "nope" / "x") == tmp_path / "nope" / "x"


def test_verify_refuses_symlink_leaf(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(UnsafePathError, match="symlink"):
        verify_safe_for_sudo(link)


def test_verify_refuses_symlink_in_middle_of_path(tmp_path):
    target = tmp_path / "target"
    (target / "inner").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(UnsafePathError, match="symlink"):
        verify_safe_for_sudo(link / "inner")


def test_verify_refuses_foreign_owner(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    with (
        patch("qemulab.utils.paths.os.getuid", return_value=os.getuid() + 1),
        pytest.raises(UnsafePathError, match="not owned"),
    ):
        verify_safe_for_sudo(d)


def test_remove_tree_never_uses_sudo_on_symlink(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    sudo_rm = MagicMock()
    with pytest.raises(OSError):
        remove_tree(link, sudo_rm)
    sudo_rm.assert_not_called()
    assert target.exists()


def test_remove_tree_sudo_fallback_verifies_path(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    sudo_rm = MagicMock()
    with patch("qemulab.utils.paths.shutil.rmtree", side_effect=PermissionError):
        remove_tree(d, sudo_rm)
    sudo_rm.assert_called_once_with(d)

    with (
        patch("qemulab.utils.paths.shutil.rmtree", side_effect=PermissionError),
        patch("qemulab.utils.paths.os.getuid", return_value=os.getuid() + 1),
        pytest.raises(UnsafePathError),
    ):
        sudo_rm.reset_mock()
        remove_tree(d, sudo_rm)
    sudo_rm.assert_not_called()


def test_ensure_private_dir_mode_and_symlink_refusal(tmp_path):
    d = ensure_private_dir(tmp_path / "x" / "priv")
    assert d.stat().st_mode & 0o777 == 0o700
    link = tmp_path / "link"
    link.symlink_to(d)
    with pytest.raises(UnsafePathError):
        ensure_private_dir(link)


def test_runtime_base_dir_uses_xdg_runtime_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    base = runtime_base_dir()
    assert base == tmp_path / "qemulab"
    assert base.stat().st_mode & 0o777 == 0o700
    assert flash_dir_for(3) == base / "flash_3"


def test_runtime_base_dir_falls_back_to_mkdtemp(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setattr(paths, "_fallback_base", None)
    monkeypatch.setattr(paths.tempfile, "tempdir", str(tmp_path))
    base = runtime_base_dir()
    assert base.parent == tmp_path
    assert base.name.startswith("qemulab-")
    assert base.stat().st_mode & 0o777 == 0o700
    assert runtime_base_dir() == base


def test_flash_dir_for_honours_override():
    assert str(flash_dir_for(2, "/srv/q/flash_")) == "/srv/q/flash_2"
