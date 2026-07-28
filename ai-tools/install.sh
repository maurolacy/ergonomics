#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for tool in ai-conversations ai-costs; do
  target="/usr/local/bin/$tool"
  ln -sf "$SCRIPT_DIR/$tool" "$target"
  echo "Linked: $target -> $SCRIPT_DIR/$tool"
done
