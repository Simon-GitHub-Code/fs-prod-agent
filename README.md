# fs-prod-agent

Local prototype of an investment-oversight desk for large asset owners (super funds, pensions, endowments, sovereign funds). It drafts and checks. It does not trade.

The running profile is `build("local")`. `build("aws")` is the same application type and stays unwired until an AWS account exists. The map is in [ARCHITECTURE.md](ARCHITECTURE.md). Agent instructions are in [AGENTS.md](AGENTS.md).

```bash
uv sync --group dev
scripts/verify
```

That command runs ruff and the fitness, unit, and integration suites. Only the fitness suite is hash-pinned. It needs no network and no API keys. Install the hooks once:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Pre-commit runs `scripts/verify`. Pre-push runs `scripts/secrets` (gitleaks 8.30.1, the version CI installs). GitHub Actions runs the same verify command, the secret scan, and `scripts/mutate`. Grok loads `.grok/rules/context-pack.md` at session start, and `CLAUDE.md` imports it for Claude Code. Project hooks return that file after an edit that changes the pack, run the pack query on a file read, ask before a write to a pinned test or quality control, and run `scripts/verify` at the end of a turn. Grok runs them once this folder is trusted (`/hooks-trust`). Claude Code runs the same scripts from `.claude/settings.json`. Neither agent loads the user-level Agor skills or the Agor MCP server here.

## Live run

`scripts/verify` stays offline. A live run puts real models in the loop:

```bash
export OLLAMA_API_KEY=...                         # https://ollama.com/settings/keys
scripts/decider --device cpu                      # strands-decider on 127.0.0.1:8000
scripts/live-smoke                                # gpt-oss:120b on Ollama Cloud
uv run python -m fs_prod_agent.desk --model gpt-oss:120b
```

The agent model is `gpt-oss:120b` on Ollama Cloud. Decisions come from the served decider. When it is down, every decision is unavailable and policy returns `failed`; a live run never falls back to the fixture. `scripts/live-smoke --fixture-decisions` keeps the scripted decisions under the live agent model, for a machine that cannot serve the decider. A model error is recorded as the run's outcome, so the trace is still written.
