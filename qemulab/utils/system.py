import shutil
import subprocess
from pathlib import Path

from qemulab.utils.logging import _logger as logger


class SystemCheck:
    REQUIRED_TOOLS = ["qemu-system-x86_64", "ip", "tmux", "sudo"]

    @staticmethod
    def check_all() -> bool:
        """Runs all system checks. Returns True if passed, False otherwise."""
        checks = [SystemCheck.check_tools, SystemCheck.check_kvm]

        results = [check() for check in checks]
        # Advisory only: never affects the result.
        SystemCheck.warn_if_sudo_needs_password()
        return all(results)

    @staticmethod
    def check_tools() -> bool:
        missing = []
        for tool in SystemCheck.REQUIRED_TOOLS:
            if not shutil.which(tool):
                missing.append(tool)

        if missing:
            logger.critical(f"Missing required tools: {', '.join(missing)}")
            return False
        return True

    @staticmethod
    def check_kvm() -> bool:
        if not Path("/dev/kvm").exists():
            logger.critical(
                "KVM acceleration not found (/dev/kvm missing). Ensure KVM modules are loaded."
            )
            return False
        return True

    @staticmethod
    def warn_if_sudo_needs_password() -> None:
        """
        Warns when sudo would prompt for a password.
        We don't want to prompt for password here, just check if we CAN sudo.
        Not a hard failure, so it returns nothing.
        """
        try:
            # sudo -n true: Check non-interactively if we have cached credentials or NOPASSWD
            subprocess.run(["sudo", "-n", "true"], check=True, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # If failed, we warn the user they might be prompted later
            logger.warning("Sudo requires password. You will be prompted in the UI/Terminal.")
