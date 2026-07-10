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
if [ ! -f "$BASHRC" ]; then
    echo "Creating ~/.bashrc..."
    echo "$SOURCE_LINE" > "$BASHRC"
    echo "Created ~/.bashrc with ergonomics config."
elif grep -qF "bashrc_base" "$BASHRC"; then
    echo "~/.bashrc already sources bashrc_base. Skipping."
else
    echo "" >> "$BASHRC"
    echo "# ergonomics: portable shell config" >> "$BASHRC"
    echo "$SOURCE_LINE" >> "$BASHRC"
    echo "Added ergonomics config to ~/.bashrc."
fi

echo ""
echo "Done. Restart your shell or run:"
echo "  source ~/.bashrc"
