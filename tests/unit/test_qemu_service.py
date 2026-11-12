from pathlib import Path

from qemulab.models.context import SessionContext
from qemulab.services.qemu import QemuCommandBuilder
from qemulab.utils.paths import flash_dir_for


def test_build_qemu_command():
    """Verify the CLI arguments for a standard QEMU node."""
    # Setup Context
    ctx = SessionContext(
        selected_board="board1",
        selected_version="1.0.0",
        kernel_path=Path("/tmp/bzImage"),
        initrd_path=Path("/tmp/rootfs.cpio"),
        node_count=4,
    )

    # Build command for Node 1
    cmd = QemuCommandBuilder.build_command(1, ctx)

    # Assertions
    cmd_str = " ".join(cmd)

    # 1. Identity
    assert "-name QEMU_board1_1" in cmd_str

    # 2. Kernel/Initrd
    assert "-kernel /tmp/bzImage" in cmd_str
    assert "-initrd /tmp/rootfs.cpio" in cmd_str

    # 3. Network (Mgmt and Data)
    # Check MAC calculation for Node 1
    assert "mac=0a:00:00:00:01:00" in cmd_str  # Mgmt
    assert "mac=0a:01:00:00:01:00" in cmd_str  # Data
    assert "ifname=tap_qlab1_0" in cmd_str
    assert "ifname=tap_qlab1_1" in cmd_str

    # 4. Flash
    assert f"path={flash_dir_for(1)}" in cmd_str


def test_build_qemu_command_node_2():
    """Verify that node ID changes affect MACs and Taps."""
    ctx = SessionContext(selected_board="board1")
    # Mock paths
    ctx.kernel_path = Path("k")
    ctx.initrd_path = Path("i")

    cmd = QemuCommandBuilder.build_command(2, ctx)
    cmd_str = " ".join(cmd)

    assert "mac=0a:00:00:00:02:00" in cmd_str
    assert "ifname=tap_qlab2_0" in cmd_str
