# Cleanup and Exit Guide

## How to Exit QemuLab

### Safe Exit (Recommended)

Press `Q` or `Ctrl+C` at any time to exit the application.

**What happens depends on the current state:**

#### Before Environment Launch

- **No cleanup needed**
- Application exits immediately
- No resources to clean up

#### During/After Environment Launch

- **Cleanup confirmation appears**
- You choose: "Yes, Cleanup" or "No, Keep Running"

### Cleanup Options

```text
┌─ Cleanup Confirmation ──────────────────────┐
│ QEMU environment is running.                │
│                                              │
│ Clean up before exit?                       │
│ • Kill QEMU instances                       │
│ • Remove network interfaces                 │
│ • Delete flash directories                  │
│ • Terminate tmux session                    │
│                                              │
│  [Yes, Cleanup]  [No, Keep Running]         │
└──────────────────────────────────────────────┘
```

#### Option 1: Yes, Cleanup (Recommended for finished work)

**Performs full cleanup:**

1. ✓ Sends shutdown signal to all QEMU instances
2. ✓ Terminates tmux session
3. ✓ Kills remaining QEMU processes
4. ✓ Removes network interfaces (tap devices, bridges)
5. ✓ Deletes flash directories (`$XDG_RUNTIME_DIR/qemulab/flash_*`)
6. ✓ Frees all allocated memory
7. ✓ Exits application

**Use when:**

- You're done testing
- You want a clean system
- You're switching scenarios

#### Option 2: No, Keep Running (Detach mode)

**Keeps environment alive:**

- ✓ QEMU instances keep running
- ✓ Tmux session stays active
- ✓ Network interfaces remain
- ✓ You can reattach later
- ✗ Application exits

**Use when:**

- You want to continue testing later
- You need to step away temporarily
- You want to attach to tmux directly

### Reattaching to Running Environment

If you chose "No, Keep Running":

```bash
# Attach to the tmux session
tmux attach -t qemulab

# Inside tmux:
# - Ctrl+B, D : Detach (keeps running)
# - Ctrl+B, X : Kill pane (stops QEMU)
# - Ctrl+C in pane : May stop QEMU
```

## What Gets Cleaned Up

### 1. QEMU Processes

```bash
# Processes killed:
QEMU_board1_1
QEMU_board1_2
QEMU_board1_3
QEMU_board1_4
```

### 2. Network Resources

```bash
# Interfaces removed:
tap_qlab1_0, tap_qlab1_1  # Node 1
tap_qlab2_0, tap_qlab2_1  # Node 2
tap_qlab3_0, tap_qlab3_1  # Node 3
tap_qlab4_0, tap_qlab4_1  # Node 4

# Bridges removed:
br_qlab      # Management bridge
qlab_data   # Data plane bridge
```

### 3. File System

```bash
# Directories removed:
$XDG_RUNTIME_DIR/qemulab/flash_1/
$XDG_RUNTIME_DIR/qemulab/flash_2/
$XDG_RUNTIME_DIR/qemulab/flash_3/
$XDG_RUNTIME_DIR/qemulab/flash_4/

# Files preserved:
logs/qemulab.log.jsonl      # Structured logs
qemulab_session_*.log       # Saved session logs
```

### 4. Tmux Session

```bash
# Session terminated:
qemulab

# All panes closed automatically
```

### 5. Memory

- All application memory freed
- Python objects garbage collected
- File handles closed
- Network sockets released

## Cleanup Logs

Watch the cleanup process in real-time:

```text
====================================================================
Starting cleanup process...
====================================================================
[INFO] Stopping QEMU instances...
[INFO] Terminating tmux session...
[INFO] Killing remaining QEMU processes...
[INFO] Removing network interfaces...
[INFO] Removing flash directories...
[INFO] Removed $XDG_RUNTIME_DIR/qemulab/flash_1
[INFO] Removed $XDG_RUNTIME_DIR/qemulab/flash_2
[INFO] Removed $XDG_RUNTIME_DIR/qemulab/flash_3
[INFO] Removed $XDG_RUNTIME_DIR/qemulab/flash_4
====================================================================
Cleanup completed successfully!
====================================================================
```

## Manual Cleanup

If cleanup fails or you need to clean up manually:

### 1. Kill QEMU Processes

```bash
# Kill all QEMU instances
sudo pkill -f "QEMU_pd"

# Verify
ps aux | grep QEMU
```

### 2. Kill Tmux Session

```bash
# Kill specific session
tmux kill-session -t qemulab

# Verify
tmux ls
```

### 3. Remove Network Interfaces

```bash
# Remove tap interfaces
for i in {1..4}; do
  sudo ip link delete tap_qlab${i}_0 2>/dev/null || true
  sudo ip link delete tap_qlab${i}_1 2>/dev/null || true
done

# Remove bridges
sudo ip link delete br_qlab 2>/dev/null || true
sudo ip link delete qlab_data 2>/dev/null || true

# Verify
ip link show | grep -E "(tap_qlab|br_qlab|qlab_data)"
```

### 4. Remove Flash Directories

```bash
# Remove all flash directories
rm -rf "$XDG_RUNTIME_DIR"/qemulab/flash_*

# Verify
ls -la "$XDG_RUNTIME_DIR"/qemulab/
```

### Complete Manual Cleanup Script

```bash
#!/bin/bash
# cleanup_qemulab.sh - Manual cleanup script

echo "Cleaning up QemuLab environment..."

# Kill QEMU
sudo pkill -f "QEMU_pd" || true

# Kill tmux
tmux kill-session -t qemulab 2>/dev/null || true

# Remove network
for i in {1..4}; do
  sudo ip link delete tap_qlab${i}_0 2>/dev/null || true
  sudo ip link delete tap_qlab${i}_1 2>/dev/null || true
done
sudo ip link delete br_qlab 2>/dev/null || true
sudo ip link delete qlab_data 2>/dev/null || true

# Remove flash
rm -rf "$XDG_RUNTIME_DIR"/qemulab/flash_* 2>/dev/null || true

echo "Cleanup complete!"
```

## Troubleshooting

### "Cleanup stuck or slow"

- **Cause**: QEMU processes not responding
- **Solution**: Wait 10 seconds, then manual cleanup

### "Network interfaces remain"

- **Cause**: Insufficient permissions
- **Solution**: Run manual cleanup with sudo

### "Flash directories not deleted"

- **Cause**: Sudo password not provided or expired
- **Solution**: Manual removal with `rm -rf` (the directories are user-owned, no sudo)

### "Tmux session still exists"

- **Cause**: Cleanup interrupted
- **Solution**: `tmux kill-session -t qemulab`

### "Memory not freed"

- **Cause**: Processes still running
- **Solution**: Kill QEMU processes manually

## Best Practices

1. **Always cleanup when done**: Press 'Q', choose "Yes, Cleanup"
2. **Save logs first**: Press 'S' before quitting
3. **Check tmux if issues**: `tmux attach -t qemulab` to debug
4. **Use detach mode for long tests**: Choose "No, Keep Running"
5. **Run manual cleanup if stuck**: Use the cleanup script above

## Emergency Exit

If the application hangs:

1. **Ctrl+Z** - Suspend process
2. **`jobs`** - See job number
3. **`kill %1`** - Kill the job
4. **Run manual cleanup** - Use script above

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Normal exit, cleanup successful |
| 1 | Error during cleanup (check logs) |
| 130 | Interrupted by user (Ctrl+C) |

## Related Commands

```bash
# Check running QEMU
ps aux | grep QEMU

# Check network interfaces
ip link show | grep -E "tap_qlab|br_qlab"

# Check tmux sessions
tmux ls

# Check flash directories
ls -la "$XDG_RUNTIME_DIR"/qemulab/

# View cleanup logs
cat logs/qemulab.log.jsonl | jq 'select(.message | contains("cleanup"))'
```
