#!/usr/bin/env python3
"""Set your Microsoft Teams status message to a random walking emoji.

Uses CGEvent mouse clicks and keyboard events to drive the Teams UI.
No API auth needed, no clipboard usage — works entirely through UI automation.

Usage:
    ./out_for_a_walk          # set walking status
    ./out_for_a_walk --clear  # clear the status message
"""

import argparse
import random
import subprocess
import time

from Quartz import (
    CGEventCreateMouseEvent,
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    CGPointMake,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
)

WALKERS = [
    "\U0001F6B6",             # 🚶
    "\U0001F6B6\U0001F3FB",   # 🚶🏻
    "\U0001F6B6\U0001F3FC",   # 🚶🏼
    "\U0001F6B6\U0001F3FD",   # 🚶🏽
    "\U0001F6B6\U0001F3FE",   # 🚶🏾
    "\U0001F6B6\U0001F3FF",   # 🚶🏿
]

# UI element offsets (in screen points, from window origin)
PROFILE_OFFSET = (987, 17)
# Offsets relative to the profile icon position
STATUS_MSG_OFFSET = (-80, 240)    # "Set status message" link
DONE_BTN_OFFSET = (-30, 520)     # Done button (status_msg + (50, 280))


def get_teams_window():
    """Get Teams window position and size. Also activates Teams."""
    script = '''
    tell application "Microsoft Teams" to activate
    delay 0.5
    tell application "System Events"
        tell process "Microsoft Teams"
            set winPos to position of window 1
            set winSize to size of window 1
            return ((item 1 of winPos) as string) & "," & ((item 2 of winPos) as string) & "," & ((item 1 of winSize) as string) & "," & ((item 2 of winSize) as string)
        end tell
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    parts = [p.strip() for p in result.stdout.strip().split(",")]
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def activate_teams():
    subprocess.run([
        "osascript", "-e",
        'tell application "Microsoft Teams" to activate'
    ], capture_output=True)


def hover(x, y):
    """Move the mouse to screen coordinates (triggers hover effects)."""
    point = CGPointMake(x, y)
    event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)


def click(x, y):
    """Send a mouse click at screen coordinates."""
    point = CGPointMake(x, y)
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.05)
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)


def paste_text(text):
    """Paste text into the focused field, preserving the user's clipboard."""
    # Save current clipboard
    saved = subprocess.run(["pbpaste"], capture_output=True)
    # Set our text
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    # Cmd+V
    event = CGEventCreateKeyboardEvent(None, 9, True)
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.05)
    event = CGEventCreateKeyboardEvent(None, 9, False)
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.3)
    # Restore clipboard
    subprocess.run(["pbcopy"], input=saved.stdout, check=True)


def cmd_a():
    """Send Cmd+A (select all) via CGEvent."""
    event = CGEventCreateKeyboardEvent(None, 0, True)  # A key down
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.05)
    event = CGEventCreateKeyboardEvent(None, 0, False)  # A key up
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)


def set_status(emoji):
    """Set Teams status message to the given emoji."""
    wx, wy, ww, wh = get_teams_window()
    px = wx + PROFILE_OFFSET[0]
    py = wy + PROFILE_OFFSET[1]

    # 1. Click profile icon
    activate_teams()
    time.sleep(0.5)
    click(px, py)
    time.sleep(1.5)

    # 2. Click "Set status message" / existing status area
    click(px + STATUS_MSG_OFFSET[0], py + STATUS_MSG_OFFSET[1])
    time.sleep(1.5)

    # 3. Select all (clear any existing text) and type the emoji
    activate_teams()
    time.sleep(0.3)
    cmd_a()
    time.sleep(0.2)
    paste_text(emoji)
    time.sleep(1.0)

    # 4. Click Done
    click(px + DONE_BTN_OFFSET[0], py + DONE_BTN_OFFSET[1])
    time.sleep(0.5)

    # 5. Dismiss the flyout by clicking the profile icon again
    click(px, py)
    time.sleep(0.3)

    print(f"Status set to {emoji}")


def clear_status():
    """Clear Teams status message by hovering to reveal the delete icon, then clicking it."""
    wx, wy, ww, wh = get_teams_window()
    px = wx + PROFILE_OFFSET[0]
    py = wy + PROFILE_OFFSET[1]

    # Status message area (same position as "Set status message" link)
    status_x = px + STATUS_MSG_OFFSET[0]
    status_y = py + STATUS_MSG_OFFSET[1]

    # 1. Click profile icon to open flyout
    activate_teams()
    time.sleep(0.5)
    click(px, py)
    time.sleep(1.5)

    # 2. Hover over the status message area to reveal the delete icon
    hover(status_x, status_y)
    time.sleep(0.8)

    # 3. Click the delete icon (bottom-right of the status text area)
    delete_x = status_x + 90
    delete_y = status_y + 20
    hover(delete_x, delete_y)
    time.sleep(0.3)
    click(delete_x, delete_y)
    time.sleep(0.8)

    # 4. Dismiss the flyout by clicking the profile icon again
    click(px, py)
    time.sleep(0.3)

    print("Status cleared")


def main():
    parser = argparse.ArgumentParser(description="Set Teams status to a walking emoji")
    parser.add_argument("--clear", action="store_true", help="Clear the status message")
    args = parser.parse_args()

    if args.clear:
        clear_status()
    else:
        emoji = random.choice(WALKERS)
        set_status(emoji)


if __name__ == "__main__":
    main()
