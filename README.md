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

Pre-commit runs `scripts/verify`. Pre-push runs `scripts/secrets` (gitleaks 8.30.1, the version CI installs). GitHub Actions runs the same verify command, the secret scan, and `scripts/mutate`. Both agents ask before a write to a pinned test or quality control. Neither loads the user-level Agor skills or the Agor MCP server here.

- **Claude Code** (`.claude/settings.json`, `scripts/context/hooks/`): a session or subagent starts with `docs/context/index.md` and two health lines (is the complexity hook answering, are the git hooks installed). An edit to production code rebuilds the pack and is silent unless a function goes over the complexity cap. A `git push` is refused while `scripts/verify` is red.
- **Grok** (`.grok/`, once this folder is trusted with `/hooks-trust`): `.grok/rules/context-pack.md` loads at session start, an edit that changes the pack returns it, and `scripts/verify` runs at the end of a turn.

## Tools over MCP

The five tools are an MCP server (`adapters/local/mcp_tools.py`), built from the manifests in `mcp_servers/catalog.py`. `build("local")` runs it in-process. `scripts/mcp-server` serves it over Streamable HTTP on `127.0.0.1:8767/mcp`, and `build("local", tool_server="http://127.0.0.1:8767/mcp")` uses it there, the way a deployment would call an AgentCore Gateway MCP target. Policy and the Strands tool gate decide before a call leaves the pipeline, so a held committee paper never reaches the server. The agent runs tools one at a time, so the audit lists them in the order it asked.

## Evals

`evals/routing/v1/cases.jsonl` holds 78 labelled cases: the two workflows, open questions, ambiguous asks, out-of-scope actions, orders phrased as questions, prompt injection, requests that need a person, and direct tool calls. Each label is what a correct decider and this policy should produce.

```bash
scripts/evals                                     # fixture tier; also runs in scripts/verify
scripts/evals --model gpt-oss:120b                # live tier: served decider + Ollama Cloud
scripts/evals --model gpt-oss:120b --record-baseline
```

The report covers verdict, route, and workflow accuracy, a route confusion matrix, unsafe approvals, over-blocking, tool trajectories, route calibration (Brier score and ECE), a confidence-threshold sweep, and latency. The release gate is zero unsafe approvals. The fixture tier is a keyword stand-in and scores badly on purpose; its report in `evals/reports/fixture.md` is the floor a real decider has to clear.

## Tracing and drift

Every request is an OpenTelemetry span carrying the decision chain: route, workflow, contract version, policy verdict, confidence, whether policy overrode the decider, tool, and outcome. Child spans cover each decision, the workflow or agent run, the Strands agent loop and tool gate, and each MCP `tools/call`. The pipeline calls only the OTel API, so with nothing configured the spans cost nothing.

```bash
scripts/observability up                          # Jaeger: UI on 127.0.0.1:16686, OTLP on :4318
uv run python -m fs_prod_agent.desk --otlp http://127.0.0.1:4318
```

On AWS the same spans would go to an ADOT collector and on to CloudWatch and AgentCore Observability. Only the endpoint changes.

`build("local", trace_log=path)` also appends each decision-chain record to a JSONL file. `scripts/drift` compares the latest window of that log with a baseline window and exits 1 on drift. Production traffic has no labels, so it watches four label-free signals: human override rate, route mix (total variation distance), mean decider confidence, and the share of failed or uncertain verdicts.

`scripts/simulate-traffic --inject <change>` replays a production-like mix and injects one change part-way through:

| change | what happens | first alert |
| --- | --- | --- |
| `confidence-decay` | a new decider is 10% less sure; every verdict is unchanged, so users see nothing | the first window after the change |
| `decider-outage` | 30% of decisions are unavailable and fail closed | the first window after the change |
| `route-flip` | a new decider sends 40% of workflow requests to the agent | one window later, and not in every window |
| `input-shift` | far more orders and injection attempts | not detected |

The last two rows are the limits. At 30 records a window the route mix is noisy (the steady state reaches a total variation of 0.17 against a 0.2 threshold), so a partial routing change shows late. An input shift is invisible here because the fixture decider does not refuse those requests, so its outputs barely move. A monitor on decider outputs cannot see a change the decider is blind to. That is what the scheduled eval run (`scripts/evals --model ...`) and an input-side monitor are for.

## Live run

`scripts/verify` stays offline. A live run puts real models in the loop:

```bash
export OLLAMA_API_KEY=...                         # https://ollama.com/settings/keys
scripts/decider --device cpu                      # strands-decider on 127.0.0.1:8000
scripts/live-smoke                                # gpt-oss:120b on Ollama Cloud
uv run python -m fs_prod_agent.desk --model gpt-oss:120b
```

The agent model is `gpt-oss:120b` on Ollama Cloud. Decisions come from the served decider. When it is down, every decision is unavailable and policy returns `failed`; a live run never falls back to the fixture. `scripts/live-smoke --fixture-decisions` keeps the scripted decisions under the live agent model, for a machine that cannot serve the decider. A model error is recorded as the run's outcome, so the trace is still written.
