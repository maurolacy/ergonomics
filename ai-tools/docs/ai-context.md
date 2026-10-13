# ai-context

_Claude: The single biggest friction is context loss. If there were one thing worth spending time (or money) on, it would be improving the externalized memory layer — making the AGENTS.md richer, keeping the conversation exports current, maybe even a structured "project journal" that captures decisions and rationale, not just code conventions. Every minute invested there pays back across every future session and every tool switch.

But that's a process improvement, not a purchase. There's nothing to buy for me.


_Mauro: Regarding your first point, i.e. a better memory system for you, perhaps we can build an ai-tool for it. Maybe you can design something tool that helps with tracking, housekeeping, integration of different sessions, etc. Something like a project logbook or "bitácora" comes to mind.


_Claude: "Bitácora" — I like that. A ship's logbook: structured, chronological, decision-oriented.

Rough sketch of what it could track:

Decisions — what was decided, why, alternatives considered (e.g. "chose toolkit 0.7.x over 0.10.x because plugins need ~1.1")
Discoveries — codebase knowledge that's expensive to re-learn (e.g. "credstore 0.3.2 requires database.servers in config, old 0.1.x didn't")
State — what's in-flight, blocked, deployed where, branch status
Contacts — who reviewed what, who owns what, team dynamics
Machine-readable (JSON/YAML), append-only entries with timestamps, queryable by project/topic/date. Any AI tool could read it at session start to bootstrap context. Could also ingest conversation exports and distill them into structured entries.

Good candidate for the ergonomics repo. I'll think about the design more concretely — we can pick it up next time, or on the personal account since it's a general-purpose tool.


_Mauro: A design note for when we build this: It uses the export functionality we already have, and then launches an instance of you to categorise it into Decisions, Discoveries, State, Contacts, etc. and build / update a searchable db from it.


_Claude: The design is sound: the conversation exports are already the raw material, the categorization is exactly the kind of task a fresh instance can do well (it's analysis, not recall), and the output becomes the persistent layer that the next instance boots from. Each cycle enriches the bitácora, which enriches the next session, which generates richer conversations to export.

A virtuous loop, built from parts that already exist.