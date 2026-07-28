#!/usr/bin/env python3
"""Export and search Cursor agent conversations from the global state DB, including thinking.

Usage:
    export_conversations.py list                          List all conversations
    export_conversations.py list -w ~/src/riddle          List conversations for a workspace
    export_conversations.py list --workspaces             List all workspaces

    export_conversations.py search <query>                Search all conversations
    export_conversations.py search <query> -w ~/src/riddle   Search within a workspace
    export_conversations.py search <query> -i             Case-insensitive search
    export_conversations.py search <query> --thinking     Search only in thinking blocks
    export_conversations.py search <query> --text         Search only in visible text
    export_conversations.py search <query> --export       Search and export matching conversations

    export_conversations.py export                        Export default workspace conversations
    export_conversations.py export -w ~/src/riddle        Export conversations for a workspace
    export_conversations.py export --all                  Export all conversations
"""

import argparse
import glob
import sqlite3
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import unquote
from urllib.parse import urlparse

DB_PATH = os.path.expanduser(
    "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
)

WORKSPACE_STORAGE_PATH = os.path.expanduser(
    "~/Library/Application Support/Cursor/User/workspaceStorage"
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exported")


# ── Workspace mapping ──────────────────────────────────────────────────────────

def build_workspace_map():
    """Scan workspaceStorage to build a mapping of workspace path → composer IDs."""
    ws_map = {}
    for ws_dir in glob.glob(os.path.join(WORKSPACE_STORAGE_PATH, "*")):
        ws_json = os.path.join(ws_dir, "workspace.json")
        state_db = os.path.join(ws_dir, "state.vscdb")
        if not os.path.exists(ws_json) or not os.path.exists(state_db):
            continue
        try:
            with open(ws_json) as f:
                ws_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        folder_uri = ws_data.get("folder", "")
        if not folder_uri:
            continue
        folder_path = uri_to_path(folder_uri)

        try:
            conn = sqlite3.connect(state_db)
            cur = conn.cursor()
            cur.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
            row = cur.fetchone()
            composer_ids = []
            if row and row[0]:
                cd = json.loads(row[0])
                composer_ids = cd.get("selectedComposerIds", [])
            conn.close()
        except Exception:
            continue

        if composer_ids:
            ws_map[folder_path] = composer_ids
    return ws_map


def uri_to_path(uri):
    """Convert a file:// URI to a filesystem path."""
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        return unquote(parsed.path)
    return uri


def resolve_workspace(workspace_arg, ws_map):
    """Find composer IDs for a workspace path (supports partial/suffix matching)."""
    workspace_arg = os.path.expanduser(workspace_arg)
    workspace_arg = os.path.abspath(workspace_arg)

    if workspace_arg in ws_map:
        return ws_map[workspace_arg], workspace_arg

    for ws_path, ids in ws_map.items():
        if ws_path.endswith(workspace_arg) or workspace_arg.endswith(ws_path.split("/")[-1]):
            return ids, ws_path

    for ws_path, ids in ws_map.items():
        if workspace_arg in ws_path or ws_path in workspace_arg:
            return ids, ws_path

    return None, None


# ── Bubble helpers ─────────────────────────────────────────────────────────────

def get_bubbles(cur, composer_id):
    prefix = f"bubbleId:{composer_id}:"
    cur.execute(
        "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?", (prefix + "%",)
    )
    bubbles = []
    for key, value in cur.fetchall():
        if value is None:
            continue
        data = json.loads(value)
        bubbles.append(data)
    bubbles.sort(key=lambda b: b.get("createdAt", ""))
    return bubbles


def format_thinking(thinking):
    if not thinking:
        return ""
    if isinstance(thinking, dict):
        return thinking.get("text", "")
    return str(thinking)


def get_bubble_text_content(bubble):
    """Extract all searchable text from a bubble."""
    parts = []
    text = bubble.get("text", "")
    if text:
        parts.append(("text", text))
    thinking = format_thinking(bubble.get("thinking"))
    if thinking:
        parts.append(("thinking", thinking))
    tool_data = bubble.get("toolFormerData")
    if tool_data and isinstance(tool_data, dict):
        raw_args = tool_data.get("rawArgs", "")
        if raw_args:
            parts.append(("tool_args", str(raw_args)))
    return parts


def get_conversation_preview(cur, composer_id):
    """Get first user message and date for a conversation."""
    bubbles = get_bubbles(cur, composer_id)
    first_date = None
    preview = ""
    bubble_count = 0
    for b in bubbles:
        if b.get("text") or format_thinking(b.get("thinking")) or b.get("toolFormerData"):
            bubble_count += 1
        if not first_date and b.get("createdAt"):
            first_date = b["createdAt"][:10]
        if not preview and b.get("type") == 1 and b.get("text"):
            preview = b["text"][:80].replace("\n", " ")
    return first_date or "unknown", bubble_count, preview


# ── Formatting ─────────────────────────────────────────────────────────────────

def format_bubble(bubble):
    lines = []
    typ = bubble.get("type")
    role = "USER" if typ == 1 else "ASSISTANT" if typ == 2 else f"TYPE_{typ}"
    created = bubble.get("createdAt", "unknown")
    bubble_id = bubble.get("bubbleId", "")

    lines.append(f"### [{role}] {created}")
    lines.append(f"<!-- bubbleId: {bubble_id} -->")
    lines.append("")

    thinking = format_thinking(bubble.get("thinking"))
    if thinking:
        lines.append("<details><summary>Thinking</summary>")
        lines.append("")
        lines.append(thinking)
        lines.append("")
        lines.append("</details>")
        lines.append("")

    text = bubble.get("text", "")
    if text:
        lines.append(text)
        lines.append("")

    tool_data = bubble.get("toolFormerData")
    if tool_data and isinstance(tool_data, dict):
        tool_name = tool_data.get("name", "unknown_tool")
        status = tool_data.get("status", "")
        raw_args = tool_data.get("rawArgs", "")
        lines.append(f"**Tool call:** `{tool_name}` (status: {status})")
        if raw_args:
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                lines.append(f"```json\n{json.dumps(args, indent=2)}\n```")
            except (json.JSONDecodeError, TypeError):
                lines.append(f"Args: {str(raw_args)[:500]}")
        lines.append("")

    tool_result = bubble.get("toolResult")
    if tool_result and isinstance(tool_result, dict):
        content = tool_result.get("content", "")
        if content:
            lines.append("**Tool result:**")
            lines.append(f"```\n{str(content)[:2000]}\n```")
            lines.append("")

    return "\n".join(lines)


# ── Commands ───────────────────────────────────────────────────────────────────

def get_composer_ids_for_args(args, cur):
    """Resolve composer IDs based on -w/--all flags."""
    if args.workspace:
        ws_map = build_workspace_map()
        ids, resolved_path = resolve_workspace(args.workspace, ws_map)
        if ids is None:
            print(f"Workspace not found: {args.workspace}")
            print(f"\nAvailable workspaces:")
            for path in sorted(ws_map.keys()):
                print(f"  {path}")
            sys.exit(1)
        print(f"Workspace: {resolved_path} ({len(ids)} conversation(s))")
        return ids
    elif hasattr(args, "all") and args.all:
        return get_all_composer_ids(cur)
    else:
        return get_all_composer_ids(cur)


def get_all_composer_ids(cur):
    cur.execute(
        "SELECT DISTINCT substr(key, 10, 36) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"
    )
    return [row[0] for row in cur.fetchall()]


def cmd_list(args, cur):
    """List conversations or workspaces."""
    if args.workspaces:
        ws_map = build_workspace_map()
        print(f"{'Convs':>5}  Workspace Path")
        print("─" * 80)
        for path in sorted(ws_map.keys()):
            ids = ws_map[path]
            print(f"{len(ids):>5}  {path}")
        print(f"\nFound {len(ws_map)} workspace(s).")
        return

    composer_ids = get_composer_ids_for_args(args, cur)

    # Build reverse workspace map for display
    ws_map = build_workspace_map()
    id_to_ws = {}
    for ws_path, ids in ws_map.items():
        for cid in ids:
            id_to_ws[cid] = ws_path

    if args.workspace:
        print(f"\n{'#':<4} {'Date':<12} {'Msgs':>5}  {'ID':<38} Preview")
    else:
        print(f"{'#':<4} {'Date':<12} {'Msgs':>5}  {'Workspace':<35} {'ID':<12} Preview")
    print("─" * 120)
    for i, cid in enumerate(composer_ids, 1):
        date, count, preview = get_conversation_preview(cur, cid)
        ws = id_to_ws.get(cid, "")
        ws_short = "~" + ws[len(os.path.expanduser("~")):] if ws.startswith(os.path.expanduser("~")) else ws
        if args.workspace:
            print(f"{i:<4} {date:<12} {count:>5}  {cid:<38} {preview}")
        else:
            print(f"{i:<4} {date:<12} {count:>5}  {ws_short:<35} {cid[:10]:<12} {preview[:40]}")
    print(f"\nFound {len(composer_ids)} conversation(s).")


def cmd_search(args, cur):
    """Search conversations for a pattern."""
    flags = re.IGNORECASE if args.case_insensitive else 0
    try:
        pattern = re.compile(args.query, flags)
    except re.error as e:
        print(f"Invalid regex pattern: {e}")
        sys.exit(1)

    composer_ids = get_composer_ids_for_args(args, cur)
    matching_conversations = {}

    print(f"\nSearching {len(composer_ids)} conversation(s) for: {args.query}")
    if args.case_insensitive:
        print("  (case-insensitive)")
    if args.thinking:
        print("  (thinking blocks only)")
    elif args.text:
        print("  (visible text only)")
    print()

    for cid in composer_ids:
        bubbles = get_bubbles(cur, cid)
        matches = []

        for bubble in bubbles:
            content_parts = get_bubble_text_content(bubble)
            for source, content in content_parts:
                if args.thinking and source != "thinking":
                    continue
                if args.text and source != "text":
                    continue

                found = list(pattern.finditer(content))
                if found:
                    typ = bubble.get("type")
                    role = "USER" if typ == 1 else "ASSISTANT" if typ == 2 else f"TYPE_{typ}"
                    created = bubble.get("createdAt", "unknown")

                    for match in found:
                        start = max(0, match.start() - 60)
                        end = min(len(content), match.end() + 60)
                        context = content[start:end].replace("\n", " ")
                        if start > 0:
                            context = "..." + context
                        if end < len(content):
                            context = context + "..."
                        matches.append({
                            "role": role,
                            "created": created,
                            "source": source,
                            "context": context,
                        })

        if matches:
            matching_conversations[cid] = matches

    if not matching_conversations:
        print("No matches found.")
        return

    # Build reverse workspace map for display
    ws_map = build_workspace_map()
    id_to_ws = {}
    for ws_path, ids in ws_map.items():
        for cid in ids:
            id_to_ws[cid] = ws_path

    print(f"Found matches in {len(matching_conversations)} conversation(s):\n")

    for cid, matches in matching_conversations.items():
        date, count, preview = get_conversation_preview(cur, cid)
        ws = id_to_ws.get(cid, "unknown")
        ws_short = "~" + ws[len(os.path.expanduser("~")):] if ws.startswith(os.path.expanduser("~")) else ws
        print(f"{'─' * 80}")
        print(f"  Conversation: {cid}")
        print(f"  Workspace: {ws_short}")
        print(f"  Date: {date}  |  Messages: {count}")
        if preview:
            print(f"  Preview: {preview}")
        print(f"  Matches: {len(matches)}")
        print()

        for m in matches[:10]:
            print(f"    [{m['role']}] {m['created']} ({m['source']})")
            print(f"      {m['context']}")
            print()

        if len(matches) > 10:
            print(f"    ... and {len(matches) - 10} more match(es)")
            print()

    if args.export:
        output_dir = args.output or OUTPUT_DIR
        print(f"\nExporting matching conversations to {output_dir}/")
        os.makedirs(output_dir, exist_ok=True)
        for cid in matching_conversations:
            export_conversation(cur, cid, output_dir)


def cmd_export(args, cur):
    """Export conversations to markdown files."""
    output_dir = args.output or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if args.workspace:
        composer_ids = get_composer_ids_for_args(args, cur)
    else:
        composer_ids = get_all_composer_ids(cur)

    print(f"Exporting {len(composer_ids)} conversation(s) to {output_dir}/")
    for cid in composer_ids:
        print(f"\n[{cid}]")
        export_conversation(cur, cid, output_dir)
    print("\nDone.")


def export_conversation(cur, composer_id, output_dir):
    bubbles = get_bubbles(cur, composer_id)
    if not bubbles:
        print(f"  No bubbles found for {composer_id}")
        return

    non_empty = [
        b for b in bubbles
        if b.get("text") or format_thinking(b.get("thinking")) or b.get("toolFormerData")
    ]

    if not non_empty:
        print(f"  No content bubbles for {composer_id}")
        return

    first_date = non_empty[0].get("createdAt", "unknown")[:10]

    lines = [
        f"# Conversation {composer_id}",
        "",
        f"- **Composer ID:** {composer_id}",
        f"- **First message:** {first_date}",
        f"- **Total bubbles:** {len(bubbles)} ({len(non_empty)} with content)",
        "",
        "---",
        "",
    ]

    for bubble in non_empty:
        lines.append(format_bubble(bubble))
        lines.append("---")
        lines.append("")

    filename = f"{first_date}_{composer_id[:8]}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    print(f"  Exported {len(non_empty)} messages to {filename}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Export and search Cursor agent conversations, including thinking."
    )
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List conversations")
    p_list.add_argument("-w", "--workspace", help="Filter by workspace path")
    p_list.add_argument("--workspaces", action="store_true", help="List workspaces instead of conversations")

    # search
    p_search = subparsers.add_parser("search", help="Search conversations")
    p_search.add_argument("query", help="Regex pattern to search for")
    p_search.add_argument("-w", "--workspace", help="Filter by workspace path")
    p_search.add_argument("-i", "--case-insensitive", action="store_true", help="Case-insensitive search")
    p_search.add_argument("--thinking", action="store_true", help="Search only in thinking blocks")
    p_search.add_argument("--text", action="store_true", help="Search only in visible text")
    p_search.add_argument("--export", action="store_true", help="Export matching conversations")
    p_search.add_argument("-o", "--output", help="Output directory for exports")

    # export
    p_export = subparsers.add_parser("export", help="Export conversations to markdown")
    p_export.add_argument("-w", "--workspace", help="Filter by workspace path")
    p_export.add_argument("--all", action="store_true", help="Export all conversations")
    p_export.add_argument("-o", "--output", help="Output directory")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if args.command in ("list", "ls"):
        cmd_list(args, cur)
    elif args.command == "search":
        cmd_search(args, cur)
    elif args.command == "export":
        cmd_export(args, cur)
    else:
        parser.print_help()

    conn.close()


if __name__ == "__main__":
    main()
