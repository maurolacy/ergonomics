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
TIMER_DROPDOWN_OFFSET = (-80, 470)  # "Clear status message after" dropdown
TIMER_1H_OFFSET = (-500, 450)       # "1 hour" menu item (floating menu position)
DONE_BTN_OFFSET = (-30, 520)     # Done button (status_msg + (50, 280))


def get_teams_window():
    """Get Teams window position and size.

    Launches Teams if not running, unminimizes if needed, and brings to front.
    """
    script = '''
    if application "Microsoft Teams" is not running then
        tell application "Microsoft Teams" to activate
        delay 3
    else
        tell application "Microsoft Teams" to activate
        delay 0.5
    end if
    tell application "System Events"
        tell process "Microsoft Teams"
            -- Wait for a window to appear (Teams may need time after activate)
            set retries to 0
            repeat while (count of windows) is 0 and retries < 10
                tell application "Microsoft Teams" to reopen
                tell application "Microsoft Teams" to activate
                delay 1
                set retries to retries + 1
            end repeat
            if (count of windows) is 0 then
                error "No Teams window found after waiting. Please open Teams first."
            end if
            -- Unminimize if needed
            if value of attribute "AXMinimized" of window 1 is true then
                set value of attribute "AXMinimized" of window 1 to false
                delay 0.5
            end if
            set winPos to position of window 1
            set winSize to size of window 1
            return ((item 1 of winPos) as string) & "," & ((item 2 of winPos) as string) & "," & ((item 1 of winSize) as string) & "," & ((item 2 of winSize) as string)
        end tell
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}")
        raise SystemExit(1)
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
    """Set Teams status message to the given emoji.

    Clears any existing status first so the flow is always consistent.
    """
    # Clear existing status (no-op if none set)
    clear_status(quiet=True)
    time.sleep(0.5)

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

    # 3. Paste the emoji into the (empty) status field
    activate_teams()
    time.sleep(0.3)
    paste_text(emoji)
    time.sleep(1.0)

    # 4. Set "Clear status message after" to 1 hour
    click(px + TIMER_DROPDOWN_OFFSET[0], py + TIMER_DROPDOWN_OFFSET[1])
    time.sleep(0.5)
    click(px + TIMER_1H_OFFSET[0], py + TIMER_1H_OFFSET[1])
    time.sleep(0.5)

    # 5. Click Done
    click(px + DONE_BTN_OFFSET[0], py + DONE_BTN_OFFSET[1])
    time.sleep(0.5)

    # 5. Dismiss the flyout by clicking the profile icon again
    click(px, py)
    time.sleep(0.3)

    print(f"Status set to {emoji}")


def clear_status(quiet=False):
    """Clear Teams status message by hovering to reveal the delete icon, then clicking it.

    If no status is set, the hover/click lands harmlessly and the flyout is dismissed.
    """
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

    if not quiet:
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
