from qemulab.config.settings import settings
from qemulab.models.context import SessionContext
from qemulab.utils.paths import flash_dir_for


class QemuCommandBuilder:
    @staticmethod
    def build_command(node_id: int, context: SessionContext) -> list[str]:
        """
        Generates the full QEMU command list for subprocess.
        """
        flash_path = flash_dir_for(node_id, settings.flash_base_path)

        # MAC Address Logic based on Node ID
        mac_mgmt = f"0a:00:00:00:0{node_id}:00"
        mac_data = f"0a:01:00:00:0{node_id}:00"

        cmd = [
            "qemu-system-x86_64",
            "-nographic",
            "-M",
            "pc",
            "-m",
            "1024",
            "-enable-kvm",
            "-name",
            f"QEMU_{context.selected_board}_{node_id}",
            # Kernel & Initrd
            "-kernel",
            str(context.kernel_path),
            "-initrd",
            str(context.initrd_path),
            "-append",
            "console=ttyS0,net.ifnames=0",
            # Network: Mgmt (eth0 -> tap0 -> mgmt bridge)
            "-netdev",
            f"tap,id=eth0,ifname=tap_qlab{node_id}_0,script=no",
            "-device",
            f"e1000,netdev=eth0,mac={mac_mgmt}",
            # Network: Data (eth1 -> tap1 -> data bridge)
            "-netdev",
            f"tap,id=eth1,ifname=tap_qlab{node_id}_1,script=no",
            "-device",
            f"e1000,netdev=eth1,mac={mac_data}",
            # Flash Storage
            "-virtfs",
            f"local,mount_tag=qemu-flash-mnt,security_model=none,path={flash_path}",
            # Serial / Monitor
            "-serial",
            "mon:stdio",
            "-echr",
            "2",  # Ctrl-B for monitor
        ]

        return cmd
