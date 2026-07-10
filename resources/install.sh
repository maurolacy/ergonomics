#!/usr/bin/env bash
# Install GNU utils and dev tools via Homebrew, and configure the shell.
#
# Prerequisites: Homebrew (https://brew.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BREWFILE="$SCRIPT_DIR/Brewfile"
BASHRC_BASE="$SCRIPT_DIR/bashrc_base"
BASHRC="$HOME/.bashrc"
SOURCE_LINE='[ -f ~/Projects/ergonomics/resources/bashrc_base ] && . ~/Projects/ergonomics/resources/bashrc_base'

# Check for Homebrew
if ! command -v brew &>/dev/null; then
    echo "Error: Homebrew is not installed."
    echo "Install it from https://brew.sh:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo "Installing packages from Brewfile..."
brew bundle --file="$BREWFILE"
echo ""
echo "Packages installed."

# Configure .bashrc to source bashrc_base
COMMENT="# ergonomics: portable shell config (history, GNU utils, aliases, completions)"
if [ ! -f "$BASHRC" ]; then
    echo "Creating ~/.bashrc..."
    printf '%s\n%s\n' "$COMMENT" "$SOURCE_LINE" > "$BASHRC"
    echo "Created ~/.bashrc with ergonomics config."
elif grep -qF "bashrc_base" "$BASHRC"; then
    echo "~/.bashrc already sources bashrc_base. Skipping."
else
    # Insert after the interactivity guard (case $- in ... esac), if present.
    # This ensures portable config loads before machine-specific customizations.
    GUARD_LINE=$(awk '/^case \$- in/{found=1} found && /^esac$/{print NR; exit}' "$BASHRC")
    if [ -n "$GUARD_LINE" ]; then
        sed -i.tmp "${GUARD_LINE}a\\
\\
${COMMENT}\\
${SOURCE_LINE}" "$BASHRC"
        rm -f "$BASHRC.tmp"
        echo "Added ergonomics config to ~/.bashrc (after interactivity guard, line $GUARD_LINE)."
    else
        # No guard found — prepend after any leading comments
        FIRST_CODE=$(awk '/^[^#]/ && !/^$/ {print NR; exit}' "$BASHRC")
        FIRST_CODE="${FIRST_CODE:-1}"
        sed -i.tmp "$((FIRST_CODE - 1))a\\
\\
${COMMENT}\\
${SOURCE_LINE}" "$BASHRC"
        rm -f "$BASHRC.tmp"
        echo "Added ergonomics config to ~/.bashrc (line $FIRST_CODE)."
    fi
fi

# Configure git-delta as the default pager (one-time)
if command -v delta &>/dev/null; then
    git config --global core.pager delta
    git config --global interactive.diffFilter "delta --color-only"
    git config --global delta.navigate true
    git config --global delta.side-by-side true
    echo "Configured git to use delta for diffs."
fi

echo ""
echo "Done. Restart your shell or run:"
echo "  source ~/.bashrc"
