# Troubleshooting QemuLab

## Sudo Password Troubleshooting

### The "Sorry, try again" Loop Issue

#### Problem
When pressing "Yes, Cleanup" in the exit dialog, you see:
```
[sudo] password for user: 
Sorry, try again.
[sudo] password for user: 
Sorry, try again.
(repeats indefinitely)
```

#### Root Cause
The cleanup process runs in a background thread and tries to execute `sudo` commands, but:
1. The TUI is blocking stdin (keyboard input)
2. Sudo can't read the password from the terminal
3. The cached password from launch has expired (default: 15 minutes)

#### Solution (Implemented)

The fix uses **subprocess.Popen with stdin.PIPE** to programmatically provide the sudo password:

```python
# OLD (broken):
subprocess.run(["sudo", "rm", "-rf", flash_dir])
# This prompts for password but can't read it!

# NEW (fixed):
proc = subprocess.Popen(
    ["sudo", "-S"] + cmd,  # -S reads password from stdin
    stdin=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
proc.communicate(input=f"{sudo_password}\n".encode())
```

### Verification Steps

After the fix, cleanup should work silently:

1. Launch environment (enter sudo password)
2. Press 'Q' to quit
3. Choose "Yes, Cleanup"
4. **No password prompt should appear**
5. Cleanup completes automatically

### If Password Still Prompts

#### Check 1: Sudo Timeout
```bash
# Check your sudo timeout setting
sudo -V | grep timeout

# Typical output:
#   Authentication timestamp timeout: 15.0 minutes
```

If you're testing and waiting > 15 minutes between launch and cleanup, the password expires.

**Solution:** Extend sudo timeout temporarily:
```bash
# In /etc/sudoers (use visudo):
Defaults timestamp_timeout=30  # 30 minutes instead of 15
```

#### Check 2: Password Not Cached

The cleanup uses `self.ctx.sudo_password` from launch. If this is `None`, cleanup will fail.

**Debug:**
```python
# In app.py, add logging before cleanup:
logging.info(f"Sudo password cached: {self.ctx.sudo_password is not None}")
```

If False, the password wasn't saved during launch.

#### Check 3: NOPASSWD Sudo (Best for Development)

For development, configure passwordless sudo for specific commands:

```bash
# Edit sudoers (CAREFUL - use visudo!)
sudo visudo

# Add this line (replace USERNAME):
USERNAME ALL=(ALL) NOPASSWD: /usr/bin/pkill, /usr/bin/ip, /bin/rm
```

This allows these cleanup commands without password.

### Manual Cleanup (No Password Issues)

If cleanup fails, use the manual script:

```bash
# Run the cleanup script
chmod +x cleanup_qemulab.sh
./cleanup_qemulab.sh

# It will prompt ONCE for sudo at the start
# Then complete all cleanup without further prompts
```

### Advanced: Debug Sudo Issues

#### Enable Sudo Logging
```bash
# In /etc/sudoers (use visudo):
Defaults log_input, log_output
Defaults logfile="/var/log/sudo.log"

# Then check the log:
sudo tail -f /var/log/sudo.log
```

#### Test Sudo with Password Pipe
```bash
# This is what the app does internally:
echo "your_password" | sudo -S ls /root

# Should work without prompting
# If it prompts, there's a system-level issue
```

#### Check Sudo Group Membership
```bash
# Verify you're in the sudo group:
groups $USER

# Should include: sudo or wheel (depending on distro)

# If not, add yourself:
sudo usermod -aG sudo $USER
# Then log out and back in
```

### Common Sudo Configurations

#### Ubuntu/Debian Default
```bash
# /etc/sudoers
%sudo   ALL=(ALL:ALL) ALL
Defaults timestamp_timeout=15
```

#### Arch Linux Default
```bash
# /etc/sudoers
%wheel ALL=(ALL:ALL) ALL
Defaults timestamp_timeout=15
```

#### Development-Friendly Config
```bash
# /etc/sudoers (use visudo!)
# Allow your user to run cleanup commands without password
your_username ALL=(ALL) NOPASSWD: /usr/bin/pkill -f QEMU_*, /usr/bin/ip link delete *, /bin/rm -rf /tmp/qemulab/*

# Extend timeout for testing
Defaults timestamp_timeout=30
```

### Testing the Fix

```bash
# 1. Launch environment
uv run python -m qemulab start
# Enter sudo password when prompted

# 2. Wait < 15 minutes (sudo timeout)
# 3. Press 'Q', choose "Yes, Cleanup"
# 4. Should complete without prompting

# 5. Verify cleanup worked:
tmux ls                    # Should not show qemulab
ps aux | grep QEMU         # Should not show QEMU processes
ip link | grep tap_qlab    # Should not show tap interfaces
ls "$XDG_RUNTIME_DIR/qemulab/"             # Should not show flash_* directories
```

### If All Else Fails

Use the manual cleanup script - it handles sudo correctly:

```bash
./cleanup_qemulab.sh
# Prompts ONCE for password at start
# Completes all cleanup
# Shows verification results
```

Or run cleanup commands manually:

```bash
# These will each prompt once:
sudo pkill -f "QEMU_pd"
tmux kill-session -t qemulab
sudo ip link delete br_qlab
sudo ip link delete qlab_data
for i in {1..4}; do
  sudo ip link delete tap_qlab${i}_0
  sudo ip link delete tap_qlab${i}_1
done
sudo rm -rf "$XDG_RUNTIME_DIR"/qemulab/flash_*
```