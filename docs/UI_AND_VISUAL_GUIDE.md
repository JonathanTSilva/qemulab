# UI Layout and Visual Guide

## Overall Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ QemuLab Manager                                                     │ ← Header
├─────────────────┬───────────────────────────────────────────────────┤
│ WIZARD STEPS    │ ● Environment: Running                            │ ← Status Bar
│ ───────────────│───────────────────────────────────────────────────│
│                 │                                                    │
│ ✓ 1. Board    │                                                   │
│ ✓ 2. Version    │         Main Content Area                         │
│ ✓ 3. Scenario   │         (Lists, Forms, Logs)                      │
│ ● 4. Node Count │                                                   │
│ ○ 5. Confirm    │                                                   │
│                 │                                                    │
│   (25% width)   │              (75% width)                           │
│                 │                                                    │
├─────────────────┴───────────────────────────────────────────────────┤
│ Q Quit │ B Back │ L Toggle Logs │ S Save Logs                       │ ← Footer
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Status Indicator (Top Right)

#### Stopped State
```
┌─────────────────────────────────────────────────┐
│ ● Environment: Stopped                          │ ← Gray, dim
└─────────────────────────────────────────────────┘
```
- **Color**: Gray (#6b7280)
- **Style**: Dim
- **When**: Initial state, after cleanup

#### Starting State
```
┌─────────────────────────────────────────────────┐
│ ◐ Environment: Starting...                      │ ← Yellow, bold
└─────────────────────────────────────────────────┘
```
- **Color**: Yellow (#ebcb8b)
- **Style**: Bold
- **When**: During launch sequence

#### Running State
```
┌─────────────────────────────────────────────────┐
│ ● Environment: Running                          │ ← Green, bold
└─────────────────────────────────────────────────┘
```
- **Color**: Green (#a3be8c)
- **Style**: Bold
- **When**: Environment fully initialized

### Wizard Sidebar

#### Visual States

**Pending Step** (Can't click)
```
○ 5. Confirmation    ← Light blue, semi-transparent
```

**Active Step** (Current)
```
● 4. Node Count      ← White, bold, highlighted background
  ▌                  ← Cyan left border
```

**Completed Step** (Clickable!)
```
✓ 1. Board         ← Green, clickable
  ↑                  ← Hover: underline + highlight
  └─ Click to jump!
```

#### Hover Effects

**Before Hover**
```
│ ✓ 1. Board    │
│ ✓ 2. Version    │
│ ✓ 3. Scenario   │
```

**On Hover (Completed Step)**
```
│ ✓ 1. Board    │ ← Highlighted background
│ ✓ 2. Version    │ ← Underlined
│ ✓ 3. Scenario   │
     ↑ Cursor here
```

### Cleanup Confirmation Modal

#### Initial Display (Yes focused)
```
┌──────────── Cleanup Confirmation ─────────────┐
│                                                │
│ QEMU environment is running.                  │
│                                                │
│ Clean up before exit?                         │
│ • Kill QEMU instances                         │
│ • Remove network interfaces                   │
│ • Delete flash directories                    │
│ • Terminate tmux session                      │
│                                                │
│  ╔═══════════════╗   ┌────────────────┐      │
│  ║ Yes, Cleanup  ║   │ No, Keep       │      │ ← Heavy border = focused
│  ╚═══════════════╝   └────────────────┘      │
│         ↑ Focused (press Enter or →)          │
└────────────────────────────────────────────────┘
```

#### After Pressing Right Arrow
```
┌──────────── Cleanup Confirmation ─────────────┐
│                                                │
│ QEMU environment is running.                  │
│                                                │
│ Clean up before exit?                         │
│ • Kill QEMU instances                         │
│ • Remove network interfaces                   │
│ • Delete flash directories                    │
│ • Terminate tmux session                      │
│                                                │
│  ┌───────────────┐   ╔════════════════╗      │
│  │ Yes, Cleanup  │   ║ No, Keep       ║      │ ← Focus moved
│  └───────────────┘   ╚════════════════╝      │
│                              ↑ Focused         │
└────────────────────────────────────────────────┘
```

**Focus Indicators:**
- **Heavy cyan border** (`╔═══╗`) around focused button
- **Bold text** on focused button
- **Tab** or **→** to move right
- **Shift+Tab** or **←** to move left

### Running Page Layout

#### While Starting (Logs Hidden)
```
┌─────────────────────────────────────────────────┐
│ Environment Status                              │
├─────────────────────────────────────────────────┤
│                                                 │
│              ◐  Loading...                      │ ← Spinner
│                                                 │
│  Press 'L' to show logs • 'S' to save          │ ← Hint
│                                                 │
└─────────────────────────────────────────────────┘
```

#### After Pressing 'L' (Logs Visible)
```
┌─────────────────────────────────────────────────┐
│ Environment Status                              │
├─────────────────────────────────────────────────┤
│              ◐  Loading...                      │
│                                                 │
│  Press 'L' to hide logs • 'S' to save          │ ← Updated hint
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ [INFO] Initializing Engine...               │ │
│ │ [INFO] Preparing Environment...              │ │
│ │ [INFO] Creating network interfaces...        │ │ ← Logs appear
│ │ [INFO] Launching QEMU Node 1...              │ │
│ │ ▼ (scrollable)                               │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### When Complete (Logs Auto-Show)
```
┌─────────────────────────────────────────────────┐
│ Environment Status                              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✓ Environment Ready!                          │ ← Success message
│  Press 'L' to hide • 'S' to save               │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ [INFO] Node 1 configured successfully.       │ │
│ │ [INFO] Node 2 configured successfully.       │ │
│ │ [INFO] ==========================            │ │
│ │ [INFO] SUCCESS! Environment is ready.        │ │
│ │ [INFO] Attach: tmux attach -t qemulab        │ │
│ │ [INFO] ==========================            │ │
│ │ ▼                                            │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Color Palette (Nord Theme)

### Background Colors
- **Main Surface**: `#2e3440` (dark blue-gray)
- **Light Surface**: `#3b4252` (lighter blue-gray)
- **Panel Gray**: `#4c566a` (medium gray)

### Accent Colors
- **Cyan**: `#88c0d0` (active items, borders)
- **Green**: `#a3be8c` (success, completed)
- **Yellow**: `#ebcb8b` (warning, starting)
- **Red**: `#bf616a` (error)

### Text Colors
- **Main Text**: `#d8dee9` (light gray)
- **Dim Text**: `#81a1c1` (muted blue)
- **White**: Used for active step

## Interactive Elements

### Clickable Items
```
Before hover:          On hover:
✓ 1. Board      →   ✓ 1. Board
                       ‾‾‾‾‾‾‾‾‾‾‾‾  ← Underline
                       [Highlighted]
```

### Buttons
```
Default:               Focused:               Primary:
┌────────────┐        ╔════════════╗        ┌────────────┐
│   Button   │        ║   Button   ║        │   Button   │
└────────────┘        ╚════════════╝        └────────────┘
                       (Cyan border)         (Cyan bg)
```

### Lists
```
Normal item:           Highlighted item:
  Item 1                ▶ Item 2          ← Left bar
  Item 2                  [Highlighted]
  Item 3                Item 3
```

## Responsive Behavior

### On Small Terminals (< 80 cols)
- Sidebar stays at 25% minimum
- Content area may scroll horizontally
- Status indicator may wrap text

### On Large Terminals (> 120 cols)
- More comfortable spacing
- Wider content area
- Better log visibility

## Accessibility Considerations

### Visual Hierarchy
1. **Status indicator** - Top right, always visible
2. **Page header** - Centered, bold, cyan
3. **Content area** - Main focus
4. **Sidebar** - Supporting navigation

### Color + Text
- ✅ Not relying on color alone
- ✅ Icons + text for states (● ◐ ○ ✓)
- ✅ Clear labels for all states

### Focus Indicators
- ✅ Heavy borders on focused elements
- ✅ Bold text for emphasis
- ✅ Consistent across UI