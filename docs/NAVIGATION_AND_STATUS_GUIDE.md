# Navigation and Status Guide

## Environment Status Indicator

### Location

**Top right corner** of the application, always visible.

### Status States

#### 🔘 Stopped (Gray)

```text
● Environment: Stopped
```

- **When**: Initial state, or after cleanup
- **Meaning**: No QEMU environment running
- **Available actions**: Start new environment

#### ◐ Starting (Yellow)

```text
◐ Environment: Starting...
```

- **When**: After clicking "Launch", during setup
- **Meaning**: Environment is being prepared
- **What's happening**:
  - Network interfaces being created
  - Flash directories being setup
  - QEMU instances launching
  - Nodes being configured

#### ● Running (Green)

```text
● Environment: Running
```

- **When**: Environment fully initialized
- **Meaning**: All nodes are running and configured
- **Available actions**:
  - Attach to tmux: `tmux attach -t qemulab`
  - View logs (press 'L')
  - Save logs (press 'S')
  - Quit with cleanup (press 'Q')

## Wizard Navigation

### Linear Navigation (Original Method)

#### Forward Navigation

- Use **arrow keys** (↑ ↓) to navigate lists
- Press **Enter** to select and move to next step
- Automatically progresses through: Board → Version → Scenario → Node Count → Confirmation

#### Backward Navigation

- Press **'B'** key to go back one step
- Can go back from any step except the first
- Preserves previous selections

### Direct Navigation (New Feature)

#### Click on Completed Steps

You can now **click on any completed step** in the left sidebar to jump directly to it:

```text
WIZARD STEPS
────────────
✓ 1. Board       ← Click here!
✓ 2. Version       ← Or here!
✓ 3. Scenario      ← Or here!
● 4. Node Count    ← Currently active
○ 5. Confirmation  ← Can't click (pending)
```

**Rules:**

- ✅ Can click: Completed steps (green ✓)
- ✅ Can click: Active step (white ●)
- ❌ Can't click: Pending steps (gray ○)

#### Visual Feedback

- **Hover**: Background highlights
- **Completed steps**: Underline on hover
- **Clickable**: Changes cursor (if terminal supports)

### Navigation Scenarios

#### Scenario 1: Change Board Mid-Flow

```text
Current: Step 4 (Node Count)
All previous steps completed

Action: Click on "1. Board"
Result:
  → Jumps to Board selection
  → Previous selection still highlighted
  → Can change board or proceed

If you change board:
  → Version list refreshes (new versions for new board)
  → Scenario list may change
  → Node count resets
  → Must reconfigure from that point
```

#### Scenario 2: Change Node Count

```text
Current: Step 5 (Confirmation)
Reviewing summary

Action: Click on "4. Node Count"
Result:
  → Jumps back to node count selection
  → Can select different number
  → Must confirm again
  → Board/Version/Scenario remain unchanged
```

#### Scenario 3: Review Earlier Selection

```text
Current: Step 3 (Scenario)

Action: Click on "2. Version"
Result:
  → Shows version list
  → Current selection highlighted
  → Can change or just press Enter to return
```

### Smart Selection Invalidation

When you change a selection at an earlier step, the wizard automatically invalidates dependent steps:

```text
Change Board:
  ✓ Board     ← Changed
  ○ Version     ← Invalidated (new board = different versions)
  ○ Scenario    ← Invalidated
  ○ Node Count  ← Invalidated

Change Version:
  ✓ Board     ← Unchanged
  ✓ Version     ← Changed
  ○ Scenario    ← Invalidated (need to reselect)
  ○ Node Count  ← Invalidated

Change Scenario:
  ✓ Board     ← Unchanged
  ✓ Version     ← Unchanged  
  ✓ Scenario    ← Changed
  ○ Node Count  ← Invalidated (scenario may have different max nodes)
```

## Modal Dialog Navigation

### Cleanup Confirmation Dialog

#### Keyboard Navigation

```text
┌─ Cleanup Confirmation ──────────┐
│ ...                              │
│  [Yes, Cleanup]  [No, Keep]     │
└──────────────────────────────────┘
```

**Navigation Keys:**

- **→ (Right Arrow)**: Move to next button
- **← (Left Arrow)**: Move to previous button
- **Tab**: Move to next button
- **Shift+Tab**: Move to previous button
- **Enter**: Select focused button
- **Escape**: Cancel (same as "No")

**Visual Feedback:**

- Focused button has **heavy cyan border**
- Focused button text is **bold**

#### Example Flow

```text
1. Dialog opens
   → "Yes, Cleanup" is focused (primary action)

2. Press Right Arrow
   → Focus moves to "No, Keep Running"

3. Press Left Arrow
   → Focus moves back to "Yes, Cleanup"

4. Press Enter
   → Executes "Yes, Cleanup" action
```

## Keyboard Shortcuts Summary

### Global

- `Q` or `Ctrl+C` - Quit (with confirmation if running)
- `B` - Go back one step
- `L` - Toggle log visibility (on running page)
- `S` - Save logs to file (on running page)

### List Navigation

- `↑` `↓` - Navigate items
- `Enter` - Select item
- `Tab` - Switch between UI elements

### Wizard Sidebar

- `Click` on completed step - Jump to that step
- `Hover` - Visual feedback

### Modal Dialogs

- `→` `←` - Navigate buttons
- `Tab` `Shift+Tab` - Navigate buttons
- `Enter` - Confirm
- `Escape` - Cancel

## Tips & Tricks

### Quick Review Workflow

```text
1. Complete wizard normally to Step 5 (Confirmation)
2. Review summary
3. Click on "2. Version" in sidebar
4. Verify correct version selected
5. Press Enter (keeps selection)
6. Click on "3. Scenario"
7. Verify scenario
8. Press Enter
9. Back at confirmation automatically
```

### Quick Change Workflow

```text
1. At Step 4 (Node Count)
2. Realize wrong scenario selected
3. Click "3. Scenario" in sidebar
4. Select different scenario
5. Automatically advances to Node Count
6. Select nodes
7. Proceed to confirmation
```

### Status Monitoring

```text
Watch the status indicator for environment state:

● Stopped (gray)
  → Safe to start new environment

◐ Starting... (yellow)
  → Wait for completion
  → Press 'L' to watch logs

● Running (green)
  → Environment ready
  → Can attach to tmux
```

## Accessibility Features

### Visual Indicators

- ✅ **Color coding**: Green (complete), Yellow (active), Gray (pending)
- ✅ **Symbols**: ✓ ● ○ for state
- ✅ **Hover effects**: Highlights clickable items
- ✅ **Focus borders**: Shows which button is focused

### Keyboard-Only Navigation

- ✅ **No mouse required**: All features accessible via keyboard
- ✅ **Tab navigation**: Works in all dialogs
- ✅ **Arrow keys**: Navigate lists and buttons
- ✅ **Enter to confirm**: Consistent across UI

### Status Visibility

- ✅ **Always visible**: Status indicator in top right
- ✅ **Clear states**: Text describes exact state
- ✅ **Color + text**: Not color-dependent
