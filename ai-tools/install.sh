#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="/usr/local/bin/ai-conversations"

ln -sf "$SCRIPT_DIR/ai-conversations" "$TARGET"
echo "Linked: $TARGET -> $SCRIPT_DIR/ai-conversations"
