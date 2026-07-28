#!/usr/bin/env python3
"""Search, list, and export Devin CLI conversations.

Data lives in ~/.local/share/devin/cli/sessions.db (SQLite) and
~/.local/share/devin/cli/summaries/ (compacted markdown).

Usage examples:
    # List sessions for this workspace
    devin-conversations list

    # List ALL sessions everywhere
    devin-conversations list --all

    # Full-text search across all conversations (current workspace)
    devin-conversations search "dylint"

    # Search everywhere
    devin-conversations search "dylint" --all

    # Export all conversations in current workspace to a directory
    devin-conversations export -o exported-conversations/

    # Export a single session
    devin-conversations export --session cyan-chinchilla -o out/

    # Show session details
    devin-conversations show cyan-chinchilla
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "devin" / "cli" / "sessions.db"
SUMMARIES_DIR = Path.home() / ".local" / "share" / "devin" / "cli" / "summaries"

# Roles we consider "conversation" (skip system/tool noise in search hits)
CONVERSATION_ROLES = {"user", "assistant"}


def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"error: database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def ts_to_local(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone().strftime(
        "%Y-%m-%d %H:%M"
    )


# -- chain walk ---------------------------------------------------------------

def walk_main_chain(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    """Walk the main chain from tip to root and return messages in order."""
    row = conn.execute(
        "SELECT main_chain_id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return []
    tip = row["main_chain_id"]
    if tip is None:
        # Fallback: return all messages ordered by node_id
        rows = conn.execute(
            "SELECT chat_message FROM message_nodes WHERE session_id = ? ORDER BY node_id",
            (session_id,),
        ).fetchall()
        return [json.loads(r["chat_message"]) for r in rows]

    rows = conn.execute(
        """
        WITH RECURSIVE chain(nid) AS (
            SELECT ?
            UNION ALL
            SELECT m.parent_node_id
            FROM message_nodes m, chain c
            WHERE m.session_id = ? AND m.node_id = c.nid AND m.parent_node_id IS NOT NULL
        )
        SELECT m.chat_message
        FROM message_nodes m
        JOIN chain c ON m.node_id = c.nid
        WHERE m.session_id = ?
        ORDER BY m.node_id ASC
        """,
        (tip, session_id, session_id),
    ).fetchall()
    return [json.loads(r["chat_message"]) for r in rows]


# -- helpers -------------------------------------------------------------------

def strip_xml_tags(text: str) -> str:
    """Remove XML-style tags for cleaner display."""
    return re.sub(r"<[^>]+>", "", text)


def truncate(text: str, max_len: int = 120) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def session_filter_clause(all_dirs: bool, cwd: str) -> tuple[str, list]:
    if all_dirs:
        return "", []
    return "WHERE working_directory = ?", [cwd]


# -- commands ------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> None:
    conn = get_db()
    cwd = os.getcwd()
    where, params = session_filter_clause(args.all, cwd)
    if not args.all and not where:
        where = "WHERE working_directory = ?"
        params = [cwd]

    rows = conn.execute(
        f"""
        SELECT s.id, s.title, s.working_directory, s.created_at, s.last_activity_at, s.model,
               (SELECT COUNT(*) FROM message_nodes mn WHERE mn.session_id = s.id) as msg_count
        FROM sessions s
        {where}
        ORDER BY s.last_activity_at DESC
        """,
        params,
    ).fetchall()

    if not rows:
        scope = "anywhere" if args.all else f"in {cwd}"
        print(f"No sessions found {scope}.")
        return

    # Header
    print(f"{'ID':<24} {'Title':<40} {'Messages':>8}  {'Last Active':<17} {'Created':<17} {'Directory'}")
    print("-" * 160)
    for r in rows:
        title = (r["title"] or "Untitled")[:39]
        directory = r["working_directory"] or ""
        if not args.all:
            directory = ""
        print(
            f"{r['id']:<24} {title:<40} {r['msg_count']:>8}  "
            f"{ts_to_local(r['last_activity_at']):<17} {ts_to_local(r['created_at']):<17} {directory}"
        )
    print(f"\n{len(rows)} session(s)")


def cmd_search(args: argparse.Namespace) -> None:
    conn = get_db()
    cwd = os.getcwd()
    pattern = args.pattern

    # Build query
    if args.all:
        join_clause = ""
        where_params: list = []
    else:
        join_clause = "JOIN sessions s ON mn.session_id = s.id"
        where_params = [cwd]

    # Search in message content
    query = f"""
        SELECT mn.session_id, mn.node_id, mn.chat_message,
               (SELECT title FROM sessions WHERE id = mn.session_id) as session_title,
               (SELECT working_directory FROM sessions WHERE id = mn.session_id) as workdir
        FROM message_nodes mn
        {join_clause}
        WHERE json_extract(mn.chat_message, '$.content') LIKE ?
          AND json_extract(mn.chat_message, '$.role') IN ('user', 'assistant')
    """
    if not args.all:
        query += " AND s.working_directory = ?"
    query += " ORDER BY mn.session_id, mn.node_id"

    like_pattern = f"%{pattern}%"
    params = [like_pattern] + where_params

    rows = conn.execute(query, params).fetchall()

    if not rows:
        scope = "anywhere" if args.all else f"in {cwd}"
        print(f"No matches for '{pattern}' {scope}.")
        return

    # Group by session
    sessions: dict[str, list] = {}
    for r in rows:
        sid = r["session_id"]
        if sid not in sessions:
            sessions[sid] = {"title": r["session_title"], "workdir": r["workdir"], "hits": []}
        msg = json.loads(r["chat_message"])
        sessions[sid]["hits"].append(msg)

    total_hits = sum(len(s["hits"]) for s in sessions.values())
    print(f"Found {total_hits} match(es) across {len(sessions)} session(s) for '{pattern}':\n")

    for sid, info in sessions.items():
        title = info["title"] or "Untitled"
        print(f"  {sid}  {title}")
        if args.all:
            print(f"    dir: {info['workdir']}")
        for hit in info["hits"][:args.max_hits]:
            role = hit.get("role", "?")
            content = hit.get("content", "")
            # Find the match context
            idx = content.lower().find(pattern.lower())
            if idx >= 0:
                start = max(0, idx - 60)
                end = min(len(content), idx + len(pattern) + 60)
                snippet = content[start:end].replace("\n", " ")
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
            else:
                snippet = truncate(content, 140)
            print(f"    [{role}] {snippet}")
        if len(info["hits"]) > args.max_hits:
            print(f"    ... and {len(info['hits']) - args.max_hits} more match(es)")
        print()


def cmd_show(args: argparse.Namespace) -> None:
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (args.session_id,)
    ).fetchone()
    if not session:
        print(f"Session '{args.session_id}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Session:   {session['id']}")
    print(f"Title:     {session['title'] or 'Untitled'}")
    print(f"Directory: {session['working_directory']}")
    print(f"Model:     {session['model']}")
    print(f"Created:   {ts_to_local(session['created_at'])}")
    print(f"Last:      {ts_to_local(session['last_activity_at'])}")

    msgs = walk_main_chain(conn, args.session_id)
    user_msgs = [m for m in msgs if m.get("role") in CONVERSATION_ROLES]
    print(f"Messages:  {len(msgs)} total, {len(user_msgs)} user/assistant")

    # Show summary if available
    summary_file = SUMMARIES_DIR / f"history_{args.session_id.replace('-', '')[:16]}.md"
    # Try to find by session id pattern
    candidates = list(SUMMARIES_DIR.glob(f"*{args.session_id.replace('-', '')[:8]}*"))
    if candidates:
        print(f"Summary:   {candidates[0]}")

    if args.messages:
        print("\n--- Conversation ---\n")
        for msg in msgs:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system" and not args.verbose:
                continue
            if role == "tool" and not args.verbose:
                # Show a brief summary of tool output
                snippet = truncate(strip_xml_tags(content), 100)
                if snippet.strip():
                    print(f"  [tool] {snippet}")
                continue
            prefix = {"user": "YOU", "assistant": "DEVIN"}.get(role, role.upper())
            print(f"=== {prefix} ===")
            if args.verbose:
                print(content)
            else:
                # For assistant messages, strip XML tags for readability
                cleaned = strip_xml_tags(content) if role == "assistant" else content
                print(cleaned.strip())
            print()


def export_session_markdown(
    conn: sqlite3.Connection, session_id: str, session_row: sqlite3.Row
) -> str:
    """Generate a readable markdown export of a session."""
    lines: list[str] = []
    title = session_row["title"] or "Untitled"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- **Session ID**: `{session_id}`")
    lines.append(f"- **Directory**: `{session_row['working_directory']}`")
    lines.append(f"- **Model**: `{session_row['model']}`")
    lines.append(f"- **Created**: {ts_to_local(session_row['created_at'])}")
    lines.append(f"- **Last Active**: {ts_to_local(session_row['last_activity_at'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

    msgs = walk_main_chain(conn, session_id)

    for msg in msgs:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "system":
            # Skip system messages in exports (rules, prompts, etc.)
            continue
        elif role == "tool":
            # Summarize tool calls briefly
            cleaned = strip_xml_tags(content).strip()
            if not cleaned:
                continue
            # Truncate very long tool outputs
            if len(cleaned) > 500:
                cleaned = cleaned[:500] + "\n\n[... output truncated ...]"
            lines.append("<details>")
            lines.append(f"<summary>Tool output ({len(content)} chars)</summary>")
            lines.append("")
            lines.append("```")
            lines.append(cleaned)
            lines.append("```")
            lines.append("</details>")
            lines.append("")
        elif role == "user":
            lines.append("## User")
            lines.append("")
            lines.append(content.strip())
            lines.append("")
        elif role == "assistant":
            lines.append("## Devin")
            lines.append("")
            # Keep assistant content as-is (may contain code blocks, etc.)
            lines.append(content.strip())
            lines.append("")

    return "\n".join(lines)


def cmd_export(args: argparse.Namespace) -> None:
    conn = get_db()
    cwd = os.getcwd()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.session:
        # Export a single session
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (args.session,)
        ).fetchone()
        if not session:
            print(f"Session '{args.session}' not found.", file=sys.stderr)
            sys.exit(1)
        sessions = [session]
    else:
        # Export all sessions in scope
        where, params = session_filter_clause(args.all, cwd)
        sessions = conn.execute(
            f"SELECT * FROM sessions {where} ORDER BY last_activity_at DESC", params
        ).fetchall()

    if not sessions:
        scope = "anywhere" if args.all else f"in {cwd}"
        print(f"No sessions found {scope}.")
        return

    exported = 0
    for session in sessions:
        sid = session["id"]
        title = session["title"] or "Untitled"
        safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]
        date_str = datetime.fromtimestamp(
            session["created_at"], tz=timezone.utc
        ).strftime("%Y%m%d")

        filename = f"{date_str}_{sid}_{safe_title}.md"
        filepath = out_dir / filename

        md = export_session_markdown(conn, sid, session)
        filepath.write_text(md, encoding="utf-8")
        exported += 1
        print(f"  exported: {filepath}")

    # Also copy relevant summaries (they use internal UUIDs, not session slugs)
    summary_dir = out_dir / "summaries"
    summary_count = 0
    if args.include_summaries and SUMMARIES_DIR.exists():
        # Collect workspace paths to match against
        workdirs = {s["working_directory"] for s in sessions}
        summary_dir.mkdir(exist_ok=True)
        for src in SUMMARIES_DIR.glob("history_*.md"):
            try:
                head = src.read_text(encoding="utf-8", errors="replace")[:2000]
                if any(wd in head for wd in workdirs):
                    dst = summary_dir / src.name
                    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                    summary_count += 1
            except OSError:
                pass

    print(f"\nExported {exported} conversation(s) to {out_dir}/")
    if summary_count:
        print(f"Copied {summary_count} summary file(s) to {summary_dir}/")


# -- main ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search, list, and export Devin CLI conversations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            examples:
              %(prog)s list                          List sessions in current directory
              %(prog)s list --all                    List all sessions everywhere
              %(prog)s search "auth refactor"        Search conversations in this workspace
              %(prog)s search "auth" --all           Search everywhere
              %(prog)s export -o exported/           Export current workspace conversations
              %(prog)s export --session ID -o out/   Export a single session
              %(prog)s show SESSION_ID               Show session details
              %(prog)s show SESSION_ID -m            Show full conversation
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", aliases=["ls"], help="List sessions")
    p_list.add_argument("--all", "-a", action="store_true", help="All directories")

    # search
    p_search = sub.add_parser("search", aliases=["grep", "find"], help="Full-text search")
    p_search.add_argument("pattern", help="Text to search for")
    p_search.add_argument("--all", "-a", action="store_true", help="Search all directories")
    p_search.add_argument(
        "--max-hits", type=int, default=5, help="Max hits shown per session (default: 5)"
    )

    # show
    p_show = sub.add_parser("show", help="Show session details")
    p_show.add_argument("session_id", help="Session ID")
    p_show.add_argument("-m", "--messages", action="store_true", help="Show messages")
    p_show.add_argument("-v", "--verbose", action="store_true", help="Include system/tool messages")

    # export
    p_export = sub.add_parser("export", help="Export conversations to markdown")
    p_export.add_argument("-o", "--output", required=True, help="Output directory")
    p_export.add_argument("--session", "-s", help="Export single session by ID")
    p_export.add_argument("--all", "-a", action="store_true", help="All directories")
    p_export.add_argument(
        "--include-summaries", action="store_true", default=True,
        help="Copy compacted summary files (default: yes)"
    )
    p_export.add_argument("--no-summaries", action="store_false", dest="include_summaries")

    args = parser.parse_args()
    cmd_map = {
        "list": cmd_list, "ls": cmd_list,
        "search": cmd_search, "grep": cmd_search, "find": cmd_search,
        "show": cmd_show,
        "export": cmd_export,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
