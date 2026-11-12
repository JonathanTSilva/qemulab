"""Tests for scripts/cleanup_qemulab.sh flash-directory handling."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "cleanup_qemulab.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")


@pytest.fixture
def fake_bin(tmp_path):
    """PATH with stubs for sudo/ip/tmux/pkill/pgrep so only the flash step does real work."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, code in {
        "sudo": 'echo "$@" >> "$SUDO_LOG"; exit 1',
        "ip": "exit 1",
        "tmux": "exit 1",
        "pkill": "exit 1",
        "pgrep": "exit 1",
    }.items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{code}\n")
        stub.chmod(0o755)
    return bin_dir


def _run(tmp_path, fake_bin, runtime):
    env = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SUDO_LOG": str(tmp_path / "sudo.log"),
    }
    if runtime is not None:
        env["XDG_RUNTIME_DIR"] = str(runtime)
    # Skip the interactive `sudo -v` check (the stub would fail it).
    script = SCRIPT.read_text().replace("if ! sudo -v; then", "if false; then")
    return subprocess.run(
        ["bash", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_removes_user_owned_flash_dirs_without_sudo(tmp_path, fake_bin):
    runtime = tmp_path / "run"
    flash = runtime / "qemulab" / "flash_1"
    (flash / "configs").mkdir(parents=True)

    result = _run(tmp_path, fake_bin, runtime)

    assert not flash.exists(), result.stdout
    log = tmp_path / "sudo.log"
    # sudo is still used for network interfaces, but never for rm
    assert "rm" not in (log.read_text() if log.exists() else "")


def test_skips_symlinked_flash_dir(tmp_path, fake_bin):
    runtime = tmp_path / "run"
    (runtime / "qemulab").mkdir(parents=True)
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("x")
    (runtime / "qemulab" / "flash_1").symlink_to(victim)

    result = _run(tmp_path, fake_bin, runtime)

    assert (victim / "keep").exists()
    assert "Skipping" in result.stdout


def test_skips_symlinked_parent(tmp_path, fake_bin):
    runtime = tmp_path / "run"
    runtime.mkdir()
    real = tmp_path / "real"
    (real / "flash_1").mkdir(parents=True)
    (runtime / "qemulab").symlink_to(real)

    result = _run(tmp_path, fake_bin, runtime)

    assert (real / "flash_1").exists()
    assert "Skipping" in result.stdout


def test_no_tmp_fallback_without_xdg_runtime_dir(tmp_path, fake_bin):
    result = _run(tmp_path, fake_bin, None)

    assert "XDG_RUNTIME_DIR is not set" in result.stdout
