"""Path helpers: private per-user working dirs and sudo-safety checks."""

import contextlib
import os
import shutil
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

PRIVATE_DIR_MODE = 0o700
_fallback_base: Path | None = None


class UnsafePathError(RuntimeError):
    """Raised when a path must not be handed to a privileged (sudo) command."""


def validate_dir(path: Path) -> bool:
    return path.exists() and path.is_dir()


def verify_safe_for_sudo(path: Path | str) -> Path:
    """Verify that `path` is safe to pass to a sudo command.

    No component of the (absolute, unresolved) path may be a symlink and the final path
    must be owned by the current user. Raises UnsafePathError otherwise.
    """
    abs_path = Path(os.path.abspath(path))
    current = Path(abs_path.anchor)
    for part in abs_path.relative_to(abs_path.anchor).parts:
        current = current / part
        try:
            st = current.lstat()
        except FileNotFoundError:
            break  # nothing below a missing component can be a symlink yet
        if stat.S_ISLNK(st.st_mode):
            raise UnsafePathError(f"Refusing sudo on {abs_path}: {current} is a symlink")
    try:
        st = abs_path.lstat()
    except FileNotFoundError:
        return abs_path
    if st.st_uid != os.getuid():
        raise UnsafePathError(f"Refusing sudo on {abs_path}: not owned by the current user")
    return abs_path


def ensure_private_dir(path: Path | str) -> Path:
    """Create `path` as the current user with mode 0700, refusing symlinks and foreign owners."""
    abs_path = Path(os.path.abspath(path))
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileExistsError):
        abs_path.mkdir(mode=PRIVATE_DIR_MODE)
    st = abs_path.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise UnsafePathError(f"{abs_path} is not a plain directory")
    if st.st_uid != os.getuid():
        raise UnsafePathError(f"{abs_path} is not owned by the current user")
    abs_path.chmod(PRIVATE_DIR_MODE)
    return abs_path


def runtime_base_dir() -> Path:
    """Per-user base dir: $XDG_RUNTIME_DIR/qemulab, else a private mkdtemp dir (0700)."""
    global _fallback_base
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and Path(runtime).is_dir():
        with contextlib.suppress(OSError, UnsafePathError):
            return ensure_private_dir(Path(runtime) / "qemulab")
    if _fallback_base is None or not _fallback_base.is_dir():
        _fallback_base = Path(tempfile.mkdtemp(prefix="qemulab-"))
    return _fallback_base


def flash_dir_for(node_id: int, base_path: str | None = None) -> Path:
    """Flash dir of a node. `base_path` is an optional prefix override (e.g. '/x/flash_')."""
    if base_path:
        return Path(f"{base_path}{node_id}")
    return runtime_base_dir() / f"flash_{node_id}"


def remove_tree(path: Path, sudo_rm: Callable[[Path], None] | None = None) -> None:
    """Remove a directory tree as the user; use `sudo_rm` only if that fails on permissions.

    Before sudo is used the path is verified (no symlink components, owned by the user).
    """
    if not path.exists() and not path.is_symlink():
        return
    try:
        shutil.rmtree(path)
    except (PermissionError, OSError):
        if sudo_rm is None or path.is_symlink():
            raise
        sudo_rm(verify_safe_for_sudo(path))
