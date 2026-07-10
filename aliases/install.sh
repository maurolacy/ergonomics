#!/usr/bin/env bash
# Install bash aliases from this repo to ~/.bash_aliases.
# Creates a backup of the existing file if present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/bash_aliases"
TARGET="$HOME/.bash_aliases"

if [ ! -f "$SOURCE" ]; then
    echo "Error: $SOURCE not found."
    exit 1
fi

# Backup existing aliases
if [ -f "$TARGET" ]; then
    BACKUP="$TARGET.bak.$(date +%Y%m%d%H%M%S)"
    cp "$TARGET" "$BACKUP"
    echo "Backed up existing aliases to $BACKUP"
fi

cp "$SOURCE" "$TARGET"
echo "Installed aliases to $TARGET"

# Source hint
echo ""
echo "To activate, either restart your shell or run:"
echo "  source ~/.bash_aliases"
