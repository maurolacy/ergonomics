#!/usr/bin/env python3
"""Set your Microsoft Teams status message to a random walking emoji.

Uses CGEvent mouse clicks and clipboard paste to drive the Teams UI.
No API auth needed — works entirely through UI automation.

Usage:
    ./out_for_a_walk          # set walking status
    ./out_for_a_walk --clear  # clear the status message
"""

import argparse
import random
import subprocess
import sys
import time

from Quartz import (
    CGEventCreateMouseEvent,
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    CGPointMake,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
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


def click(x, y):
    """Send a mouse click at screen coordinates."""
    point = CGPointMake(x, y)
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.05)
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, event)


def cmd_v():
    """Send Cmd+V (paste) via CGEvent."""
    event = CGEventCreateKeyboardEvent(None, 9, True)  # V key down
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)
    time.sleep(0.05)
    event = CGEventCreateKeyboardEvent(None, 9, False)  # V key up
    CGEventSetFlags(event, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event)


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

    # Put emoji on clipboard
    subprocess.run(["pbcopy"], input=emoji.encode("utf-8"), check=True)

    # 1. Click profile icon
    activate_teams()
    time.sleep(0.5)
    click(px, py)
    time.sleep(1.5)

    # 2. Click "Set status message"
    click(px + STATUS_MSG_OFFSET[0], py + STATUS_MSG_OFFSET[1])
    time.sleep(1.5)

    # 3. Select all (clear any existing text) and paste emoji
    activate_teams()
    time.sleep(0.3)
    cmd_a()
    time.sleep(0.2)
    cmd_v()
    time.sleep(1.0)

    # 4. Click Done
    click(px + DONE_BTN_OFFSET[0], py + DONE_BTN_OFFSET[1])
    time.sleep(0.5)

    # 5. Dismiss the flyout by clicking on the main Teams area
    click(wx + ww // 2, wy + wh // 2)
    time.sleep(0.3)

    print(f"Status set to {emoji}")


def clear_status():
    """Clear Teams status message by setting it to empty."""
    wx, wy, ww, wh = get_teams_window()
    px = wx + PROFILE_OFFSET[0]
    py = wy + PROFILE_OFFSET[1]

    # Put empty string on clipboard
    subprocess.run(["pbcopy"], input=b"", check=True)

    # 1. Click profile icon
    activate_teams()
    time.sleep(0.5)
    click(px, py)
    time.sleep(1.5)

    # 2. Click "Set status message"
    click(px + STATUS_MSG_OFFSET[0], py + STATUS_MSG_OFFSET[1])
    time.sleep(1.5)

    # 3. Select all and delete (paste empty)
    activate_teams()
    time.sleep(0.3)
    cmd_a()
    time.sleep(0.2)
    cmd_v()
    time.sleep(1.0)

    # 4. Click Done
    click(px + DONE_BTN_OFFSET[0], py + DONE_BTN_OFFSET[1])
    time.sleep(0.5)

    # 5. Dismiss the flyout
    click(wx + ww // 2, wy + wh // 2)
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
