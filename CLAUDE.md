# Claude Code

The agent contract is AGENTS.md. It applies to Claude Code unchanged. The context pack is generated, and `scripts/context/build.py` rewrites it.

@AGENTS.md

@.grok/rules/context-pack.md

`.claude/settings.json` runs the same hook scripts as Grok, from `.grok/hooks/`. It asks before a write to a pinned file, returns the pack after a file read or edit, and runs `scripts/verify` at the end of a turn. It also turns off the user-level Agor skills and the Agor MCP server. They are not used in this repository.
