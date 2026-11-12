import logging
import subprocess

from qemulab.config.settings import settings

logger = logging.getLogger(__name__)


class NetworkService:
    @staticmethod
    def run_sudo(cmd: list[str], check: bool = True, sudo_password: str | None = None) -> bool:
        """Helper to run commands with sudo, optionally using a password."""
        try:
            if sudo_password:
                # Use password via stdin
                proc = subprocess.Popen(
                    ["sudo", "-S"] + cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=f"{sudo_password}\n".encode())
                return proc.returncode == 0
            # Try without password (may use cached credentials)
            subprocess.run(
                ["sudo"] + cmd, check=check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except subprocess.CalledProcessError:
            if check:
                logger.debug(f"Command failed: {' '.join(cmd)}")
            return False

    @classmethod
    def setup_management_bridge(cls, sudo_password: str | None = None):
        """Creates the management bridge (br_mgmt) and assigns IP."""
        if cls.run_sudo(
            ["ip", "link", "show", settings.network.mgmt.bridge_name],
            check=False,
            sudo_password=sudo_password,
        ):
            logger.debug(f"Bridge {settings.network.mgmt.bridge_name} already exists.")
        else:
            logger.info(f"Creating management bridge: {settings.network.mgmt.bridge_name}")
            cls.run_sudo(
                ["ip", "link", "add", "name", settings.network.mgmt.bridge_name, "type", "bridge"],
                sudo_password=sudo_password,
            )
            cls.run_sudo(
                ["ip", "link", "set", "dev", settings.network.mgmt.bridge_name, "up"],
                sudo_password=sudo_password,
            )

            # Set IP, e.g. 192.0.2.1/24
            cidr = f"{settings.network.mgmt.base_ip}/{settings.network.mgmt.netmask}"
            cls.run_sudo(
                ["ip", "addr", "add", cidr, "dev", settings.network.mgmt.bridge_name],
                sudo_password=sudo_password,
            )

    @classmethod
    def setup_data_bridge(cls, bridge_name: str | None = None, sudo_password: str | None = None):
        """Creates the data plane bridge for inter-VM communication."""
        bridge_name = bridge_name or settings.network.data_bridge_name
        if not cls.run_sudo(
            ["ip", "link", "show", bridge_name], check=False, sudo_password=sudo_password
        ):
            logger.info(f"Creating data bridge: {bridge_name}")
            cls.run_sudo(
                ["ip", "link", "add", "name", bridge_name, "type", "bridge"],
                sudo_password=sudo_password,
            )
            cls.run_sudo(
                ["ip", "link", "set", "dev", bridge_name, "up"], sudo_password=sudo_password
            )

    @classmethod
    def create_tap_interfaces(cls, node_id: int, sudo_password: str | None = None):
        """Creates the two TAP interfaces required for a node."""
        # Tap 0: Management (connected to br_mgmt)
        tap0 = f"tap_qlab{node_id}_0"
        if not cls.run_sudo(["ip", "link", "show", tap0], check=False, sudo_password=sudo_password):
            cls.run_sudo(
                ["ip", "tuntap", "add", "dev", tap0, "mode", "tap", "group", "netdev"],
                sudo_password=sudo_password,
            )
            cls.run_sudo(["ip", "link", "set", "dev", tap0, "up"], sudo_password=sudo_password)
            cls.run_sudo(
                ["ip", "link", "set", "dev", tap0, "master", settings.network.mgmt.bridge_name],
                sudo_password=sudo_password,
            )

        # Tap 1: Data (connected to the data bridge)
        tap1 = f"tap_qlab{node_id}_1"
        bridge_data = settings.network.data_bridge_name
        if not cls.run_sudo(["ip", "link", "show", tap1], check=False, sudo_password=sudo_password):
            cls.run_sudo(
                ["ip", "tuntap", "add", "dev", tap1, "mode", "tap", "group", "netdev"],
                sudo_password=sudo_password,
            )
            cls.run_sudo(["ip", "link", "set", "dev", tap1, "up"], sudo_password=sudo_password)
            cls.run_sudo(
                ["ip", "link", "set", "dev", tap1, "master", bridge_data],
                sudo_password=sudo_password,
            )

    @classmethod
    def cleanup(cls, node_count: int = 10, sudo_password: str | None = None):
        """Aggressive cleanup of all QEMU-related network interfaces."""
        logger.info("Cleaning up network interfaces...")

        # Remove Taps
        for i in range(1, node_count + 1):
            for j in [0, 1]:
                tap = f"tap_qlab{i}_{j}"
                cls.run_sudo(
                    ["ip", "link", "delete", tap], check=False, sudo_password=sudo_password
                )

        # Remove Bridges
        cls.run_sudo(
            ["ip", "link", "delete", settings.network.data_bridge_name],
            check=False,
            sudo_password=sudo_password,
        )
        cls.run_sudo(
            ["ip", "link", "delete", settings.network.mgmt.bridge_name],
            check=False,
            sudo_password=sudo_password,
        )
