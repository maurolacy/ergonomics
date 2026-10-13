# Tools

## ai-conversations
    - ~~Add claude conversations support.~~ (done)
    - Add sort by column (date, model, conversations, ...).
    - Add full search results (--full).

## ai-costs
    - ~~Add devin costs / cost estimations.~~ (done)

## ai-context

~~Basic tool for context DB / persistent memory.~~ (done — v0.1)
See discussion in [ai-context.md](./docs/ai-context.md).
    - Test with real conversations (needs ANTHROPIC_API_KEY or OPENROUTER_API_KEY).
    - Bulk ingest historical conversations.
    - Tune categorization prompt for better extraction quality.
    - Add `ai-context import` to directly import from Devin summaries (without re-exporting).
    - Add `ai-context merge` to deduplicate entries across overlapping sessions.
    - Add `ai-context export` to dump entries as markdown/JSON for bootstrapping new sessions.