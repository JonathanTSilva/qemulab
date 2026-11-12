# Log Viewing and Export Guide

## Understanding Log Visibility

### During Launch

- **Loading Spinner shows**: Environment is being prepared
- **Logs are hidden by default**: To keep the UI clean and focused
- **Press 'L'**: To show/hide logs in real-time

### After Launch Completes

- **Logs automatically appear**: Full visibility of what happened
- **Loading spinner disappears**: Process is complete
- **You can scroll the logs**: Use arrow keys, Page Up/Down, or mouse wheel

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `L` | Toggle Logs | Show/hide the log output |
| `S` | Save Logs | Export logs to a timestamped file |
| `Q` | Quit | Exit the application |
| `B` | Back | Go to previous step (not available during launch) |

## Copying Log Content

Since this is a Terminal UI, you **cannot select text with your mouse** like in a GUI application. Instead:

### Option 1: Save Logs to File (Recommended)

1. Press `S` while viewing logs
2. Logs are saved to: `qemulab_session_YYYYMMDD_HHMMSS.log`
3. Open the file in any text editor
4. Copy whatever you need

Example:

```bash
# After pressing 'S' in the app
$ cat qemulab_session_20250119_143052.log
[INFO] Initializing Engine...
[INFO] Preparing Environment...
...
```

### Option 2: Use Tmux Copy Mode

If you're running qemulab inside tmux:

1. Press `Ctrl+B` then `[` to enter copy mode
2. Use arrow keys to navigate
3. Press `Space` to start selection
4. Move to end of selection
5. Press `Enter` to copy
6. Press `Ctrl+B` then `]` to paste

### Option 3: Terminal Scrollback

Some terminals allow selecting text from scrollback:

- **iTerm2 (macOS)**: Hold `Cmd` while selecting
- **Windows Terminal**: Hold `Shift` while selecting
- **GNOME Terminal**: Hold `Shift` while selecting

However, this only works for terminal output, not the Textual TUI content.

## Log File Format

Saved logs are plain text with this format:

```text
[INFO] Message here
[ERROR] Error message
[DEBUG] Debug details
```

## Viewing Logs Later

All logs are also written to:

```text
logs/qemulab.log.jsonl
```

This is a structured JSON log that can be parsed:

```bash
# View all logs
cat logs/qemulab.log.jsonl | jq

# Filter by level
cat logs/qemulab.log.jsonl | jq 'select(.level == "ERROR")'

# Search for specific message
cat logs/qemulab.log.jsonl | jq 'select(.message | contains("Node 1"))'
```

## Troubleshooting

### "Logs won't appear when I press 'L'"

- Make sure you're on the "Running" page (after clicking Launch)
- Check the hint text at the top - it should say "Press 'L' to show/hide logs"

### "Saved log file is empty"

- Make sure you're pressing 'S' after some logs have appeared
- Check the current directory: `ls -la qemulab_session_*.log`

### "I can't scroll the logs"

- Use arrow keys: ↑ ↓
- Use Page Up / Page Down
- Use Home / End to jump to start/end
- Mouse wheel should work in most terminals

## Best Practices

1. **Start with logs hidden**: Keep UI clean during quick runs
2. **Show logs if something fails**: Press 'L' to see what went wrong
3. **Save logs before quitting**: Press 'S' to preserve the session log
4. **Use structured logs for automation**: Parse `logs/qemulab.log.jsonl` in scripts
