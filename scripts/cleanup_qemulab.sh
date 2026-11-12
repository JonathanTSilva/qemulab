#!/usr/bin/env bash
# cleanup_qemulab.sh - Manual cleanup script for QemuLab environment
# Use this if automatic cleanup fails or you need to clean up manually

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}╔═══════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║   QemuLab Manual Cleanup Script      ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check if running with sudo or can sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠  This script requires sudo privileges.${NC}"
    echo "Testing sudo access..."
    
    # Try to get sudo access upfront
    if ! sudo -v; then
        echo -e "${RED}✗ Failed to obtain sudo privileges${NC}"
        echo "Please run: sudo $0"
        exit 1
    fi
    
    # Keep sudo alive in background
    while true; do sudo -n true; sleep 50; kill -0 "$" || exit; done 2>/dev/null &
fi

cleanup_count=0

# 1. Kill QEMU processes (no sudo needed for pkill)
echo -e "${YELLOW}[1/5]${NC} Killing QEMU processes..."
if pkill -f "QEMU_pd" 2>/dev/null; then
    echo -e "${GREEN}  ✓ QEMU processes terminated${NC}"
    ((cleanup_count++))
    sleep 1
else
    echo -e "${GREEN}  ✓ No QEMU processes found${NC}"
fi

# 2. Kill tmux session (no sudo needed)
echo -e "${YELLOW}[2/5]${NC} Terminating tmux session..."
if tmux kill-session -t qemulab 2>/dev/null; then
    echo -e "${GREEN}  ✓ Tmux session terminated${NC}"
    ((cleanup_count++))
else
    echo -e "${GREEN}  ✓ No tmux session found${NC}"
fi

# 3. Remove network interfaces (needs sudo)
echo -e "${YELLOW}[3/5]${NC} Removing network interfaces..."
iface_count=0

# Remove tap interfaces
for i in {1..10}; do
    if sudo ip link delete tap_qlab${i}_0 2>/dev/null; then
        ((iface_count++))
    fi
    if sudo ip link delete tap_qlab${i}_1 2>/dev/null; then
        ((iface_count++))
    fi
done

# Remove bridges
if sudo ip link delete br_qlab 2>/dev/null; then
    ((iface_count++))
fi
if sudo ip link delete qlab_data 2>/dev/null; then
    ((iface_count++))
fi

if [ $iface_count -gt 0 ]; then
    echo -e "${GREEN}  ✓ Removed $iface_count network interfaces${NC}"
    ((cleanup_count++))
else
    echo -e "${GREEN}  ✓ No network interfaces found${NC}"
fi

# 4. Remove flash directories (needs sudo)
echo -e "${YELLOW}[4/5]${NC} Removing flash directories..."
flash_count=0

for i in {1..10}; do
    flash_dir="${XDG_RUNTIME_DIR:-/tmp}/qemulab/flash_${i}"
    if [ -d "$flash_dir" ]; then
        if sudo rm -rf "$flash_dir" 2>/dev/null; then
            ((flash_count++))
        fi
    fi
done

if [ $flash_count -gt 0 ]; then
    echo -e "${GREEN}  ✓ Removed $flash_count flash directories${NC}"
    ((cleanup_count++))
else
    echo -e "${GREEN}  ✓ No flash directories found${NC}"
fi

# 5. Final verification
echo -e "${YELLOW}[5/5]${NC} Verifying cleanup..."

verify_count=0

# Check QEMU
if pgrep -f "QEMU_pd" >/dev/null 2>&1; then
    echo -e "${RED}  ✗ QEMU processes still running:${NC}"
    pgrep -f "QEMU_pd" | head -3
else
    echo -e "${GREEN}  ✓ No QEMU processes${NC}"
    ((verify_count++))
fi

# Check tmux
if tmux has-session -t qemulab 2>/dev/null; then
    echo -e "${RED}  ✗ Tmux session still exists${NC}"
else
    echo -e "${GREEN}  ✓ No tmux session${NC}"
    ((verify_count++))
fi

# Check network interfaces
if ip link show 2>/dev/null | grep -qE "(tap_qlab|br_qlab|qlab_data)"; then
    echo -e "${RED}  ✗ Network interfaces still exist:${NC}"
    ip link show 2>/dev/null | grep -E "(tap_qlab|br_qlab|qlab_data)" | head -3
else
    echo -e "${GREEN}  ✓ No network interfaces${NC}"
    ((verify_count++))
fi

# Check flash directories
if ls -d "${XDG_RUNTIME_DIR:-/tmp}"/qemulab/flash_* 2>/dev/null | head -1 >/dev/null; then
    echo -e "${RED}  ✗ Flash directories still exist:${NC}"
    ls -d "${XDG_RUNTIME_DIR:-/tmp}"/qemulab/flash_* 2>/dev/null | head -3
else
    echo -e "${GREEN}  ✓ No flash directories${NC}"
    ((verify_count++))
fi

echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════╗${NC}"

if [ $verify_count -eq 4 ]; then
    echo -e "${GREEN}║      ✓ CLEANUP SUCCESSFUL!           ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════╝${NC}"
    exit 0
elif [ $cleanup_count -gt 0 ]; then
    echo -e "${YELLOW}║   ⚠  CLEANUP PARTIALLY SUCCESSFUL    ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Some resources were cleaned but verification failed.${NC}"
    echo -e "${YELLOW}This may be normal if resources didn't exist.${NC}"
    exit 0
else
    echo -e "${GREEN}║    ✓ ALREADY CLEAN (Nothing to do)   ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════╝${NC}"
    exit 0
fi
