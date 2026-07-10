#!/usr/bin/env bash
# Install bash aliases from this repo to ~/.bash_aliases_base,
# and set up ~/.bash_aliases to source it with room for local overrides.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/bash_aliases"
BASE="$HOME/.bash_aliases_base"
LOCAL="$HOME/.bash_aliases"

if [ ! -f "$SOURCE" ]; then
    echo "Error: $SOURCE not found."
    exit 1
fi

# Install base aliases
if [ -f "$BASE" ]; then
    BACKUP="$BASE.bak.$(date +%Y%m%d%H%M%S)"
    cp "$BASE" "$BACKUP"
    echo "Backed up existing base to $BACKUP"
fi
cp "$SOURCE" "$BASE"
echo "Installed base aliases to $BASE"

# Set up ~/.bash_aliases to source base + hold local aliases
if [ ! -f "$LOCAL" ]; then
    cat > "$LOCAL" <<'EOF'
# Source base aliases (managed by ergonomics — use sync.sh to update)
[ -f ~/.bash_aliases_base ] && . ~/.bash_aliases_base

# Local aliases (machine-specific, not synced)
EOF
    echo "Created $LOCAL (sources base, ready for local aliases)."
elif ! grep -qF 'bash_aliases_base' "$LOCAL"; then
    # Prepend base sourcing to existing local file
    TMPFILE=$(mktemp)
    cat > "$TMPFILE" <<'EOF'
# Source base aliases (managed by ergonomics — use sync.sh to update)
[ -f ~/.bash_aliases_base ] && . ~/.bash_aliases_base

# Local aliases (machine-specific, not synced)
EOF
    cat "$LOCAL" >> "$TMPFILE"
    mv "$TMPFILE" "$LOCAL"
    echo "Added base sourcing to existing $LOCAL."
else
    echo "$LOCAL already sources base. Skipping."
fi

echo ""
echo "To activate, either restart your shell or run:"
echo "  source ~/.bash_aliases"
