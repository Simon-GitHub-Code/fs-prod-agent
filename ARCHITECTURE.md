# Architecture

Hexagonal decision pipeline for an investment oversight desk. The system drafts and checks. It does not trade.

The fitness suite is the authority for this shape. Unit tests check one module. Integration tests run `build("local")`. The agent contract is [AGENTS.md](AGENTS.md).

```
context → decide → authorize → execute → observe → evaluate
```

`Pipeline.run` is the only route branch. A workflow spec names any follow-up contract, and the steps on that spec are functions the local runner calls. The agent runner returns the answer.

`build("local")` wires in-memory adapters and is the profile this repository runs. `build("aws")` returns the same `App` type and raises `AwsProfileUnavailable` until an account exists. Only `composition.py` imports adapters.

Decider recommends with a choice, a score, or a noul. Policy disposes. An unavailable or invalid decision is `failed`.

| Path | Kind | What it does |
| --- | --- | --- |
| `performance_pack` | workflow | Quarterly total-fund return against the strategic asset allocation. |
| `mandate_check` | workflow | Holdings against investment policy ranges, then one materiality question. |
| `oversight_analyst` | agent | An open question. Tools are names. The gateway calls them. |

`submit_committee_paper` is the mutating tool. Policy returns `review`. The local book is one quarter: the fund returned 3.10% against an SAA of 2.40%, and private markets sit above the policy band.

`docs/context/` and `.grok/rules/context-pack.md` are generated. The fitness suite rejects a hand edit. Grok loads the rules file at session start, and `CLAUDE.md` imports it for Claude Code. An edit that changes the pack returns that file from `.grok/hooks/context_pack.py`. A read returns the pack query. A write to a pinned fitness test or quality control asks for approval first. Unit and integration tests are not pinned.

```bash
scripts/verify
```
