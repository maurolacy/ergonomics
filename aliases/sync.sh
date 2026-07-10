#!/usr/bin/env bash
# Bi-directional sync between ~/.bash_aliases and the repo copy.
#
# Usage:
#   ./sync.sh          show diff between local and repo
#   ./sync.sh pull     pull repo changes into local ~/.bash_aliases
#   ./sync.sh push     push local changes into the repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$SCRIPT_DIR/bash_aliases"
LOCAL="$HOME/.bash_aliases"

if [ ! -f "$REPO" ]; then
    echo "Error: repo aliases not found at $REPO"
    exit 1
fi

if [ ! -f "$LOCAL" ]; then
    echo "No ~/.bash_aliases found. Run install.sh first."
    exit 1
fi

ACTION="${1:-diff}"

case "$ACTION" in
    diff|status)
        if diff -q "$LOCAL" "$REPO" > /dev/null 2>&1; then
            echo "In sync. No differences."
        else
            echo "Differences between local (~/.bash_aliases) and repo:"
            echo ""
            diff --color=auto -u "$LOCAL" "$REPO" || true
            echo ""
            echo "Run './sync.sh pull' to pull repo changes into local."
            echo "Run './sync.sh push' to push local changes into the repo."
        fi
        ;;
    pull)
        if diff -q "$LOCAL" "$REPO" > /dev/null 2>&1; then
            echo "Already in sync. Nothing to pull."
            exit 0
        fi
        echo "Pulling repo changes into ~/.bash_aliases..."
        echo ""
        diff --color=auto -u "$LOCAL" "$REPO" || true
        echo ""
        BACKUP="$LOCAL.bak.$(date +%Y%m%d%H%M%S)"
        read -rp "Apply these changes to ~/.bash_aliases? (backup at $BACKUP) [y/N] " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            cp "$LOCAL" "$BACKUP"
            cp "$REPO" "$LOCAL"
            echo "Local updated from repo (backup: $BACKUP)"
            echo "Run 'source ~/.bash_aliases' to activate."
        else
            echo "Aborted."
        fi
        ;;
    push)
        if diff -q "$LOCAL" "$REPO" > /dev/null 2>&1; then
            echo "Already in sync. Nothing to push."
            exit 0
        fi
        echo "Pushing local changes into the repo..."
        echo ""
        diff --color=auto -u "$REPO" "$LOCAL" || true
        echo ""
        read -rp "Apply these changes to the repo? [y/N] " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            cp "$LOCAL" "$REPO"
            echo "Repo updated from ~/.bash_aliases"
        else
            echo "Aborted."
        fi
        ;;
    *)
        echo "Usage: $0 [diff|pull|push]"
        echo ""
        echo "  diff   show differences (default)"
        echo "  pull   pull repo changes into local ~/.bash_aliases"
        echo "  push   push local changes into the repo"
        exit 1
        ;;
esac
