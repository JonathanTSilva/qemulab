# QemuLab Quick Reference

## Keyboard Shortcuts

### Global

- `Q` or `Ctrl+C` - Quit application (with cleanup confirmation)
- `B` - Go back to previous step (before launch)

### Navigation

- `B` - Go back to previous step
- `↑` `↓` - Navigate lists
- `Enter` - Select item
- `Tab` - Switch between UI elements

### Running Page (During/After Launch)

- `L` - Toggle log visibility (show/hide)
- `S` - Save logs to file (`qemulab_session_YYYYMMDD_HHMMSS.log`)

### Log Viewing

- `↑` `↓` - Scroll logs line by line
- `PgUp` `PgDn` - Scroll logs page by page
- `Home` - Jump to top of logs
- `End` - Jump to bottom of logs

## Workflow

```text
┌─────────────────────────────────────────┐
│ ● Environment: Stopped    [Status]     │ ← Always visible
├─────────────────────────────────────────┤

1. Select Board (board1, board2, etc.)
   └─> Press Enter OR click completed step to go back

2. Select Version (image build)
   └─> Press Enter OR click step 1 to change board

3. Select Scenario (ospf, isis, etc.)
   └─> Press Enter OR click any previous step

4. Select Number of Nodes (1-4)
   └─> Press Enter OR click step 3 to change scenario

5. Review Summary
   └─> Press Enter on "LAUNCH ENVIRONMENT"
   └─> Or click any step to modify

6. Enter Sudo Password (always required)
   └─> Type password, press Enter
   └─> Status changes to: ◐ Starting...

7. Wait for Launch
   └─> Press 'L' to show/hide logs in real-time
   └─> Environment starts automatically
   └─> Status changes to: ● Running (green)

8. Environment Ready!
   └─> Logs appear automatically
   └─> Press 'S' to save logs
   └─> Attach to tmux: `tmux attach -t qemulab`
   └─> Press 'Q' to quit (with cleanup dialog)
```

## File Locations

### Logs

- **Live logs**: `logs/qemulab.log.jsonl` (structured JSON)
- **Saved logs**: `qemulab_session_*.log` (plain text, current directory)

### Configuration

- **Global config**: `qemulab/config/defaults.yaml`
- **Scenarios**: `scenarios/<scenario_name>/`
  - `scenario.json` - Scenario configuration
  - `cfg_dut1`, `cfg_dut2`, etc. - Device configs

### Runtime Data

- **Flash storage**: `$XDG_RUNTIME_DIR/qemulab/flash_1/`, `$XDG_RUNTIME_DIR/qemulab/flash_2/`, etc.
- **Network interfaces**: `tap_qlab1_0`, `tap_qlab1_1`, etc.
- **Bridges**: `br_qlab`, `qlab_data`

## Tmux Session

After launch completes, attach to the tmux session:

```bash
# Attach to the session
tmux attach -t qemulab

# Detach from session (keeps it running)
Ctrl+B, then D

# List sessions
tmux ls

# Kill session
tmux kill-session -t qemulab
```

### Tmux Pane Navigation

- `Ctrl+B` then `↑↓←→` - Switch between panes
- `Ctrl+B` then `z` - Zoom current pane (toggle fullscreen)
- `Ctrl+B` then `[` - Enter copy mode (for selecting text)

## Common Issues

| Problem | Solution |
|---------|----------|
| "Can't select text" | Press `S` to save logs to file, then open file |
| "Logs not appearing" | Press `L` to toggle log visibility |
| "Stuck at login prompt" | Check tmux session: `tmux attach -t qemulab` |
| "Network error" | Ensure you entered sudo password correctly |
| "QEMU won't start" | Check `logs/qemulab.log.jsonl` for errors |

## Tips

- 💡 **Save logs regularly**: Press `S` before quitting
- 💡 **Use structured logs**: Parse `logs/qemulab.log.jsonl` with `jq`
- 💡 **Hide logs initially**: Keep UI clean, show only when needed
- 💡 **Check tmux first**: Most issues are visible in the tmux session
- 💡 **Read the full logs**: The saved file shows everything

## Getting Help

1. Save logs: Press `S`
2. Check structured logs: `cat logs/qemulab.log.jsonl | jq`
3. Attach to tmux: `tmux attach -t qemulab`
4. Check QEMU panes for errors
5. Share log files when asking for help
