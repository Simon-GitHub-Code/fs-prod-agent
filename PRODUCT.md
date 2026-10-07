# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The person at this local desk types a question and reads an audit of the stages that ran. The same person opens five worked cases: the quarterly briefing, the mandate breach, the open manager question, a refused order, and a committee paper held for a person.

The repository describes the desk's operator as an analyst at a large asset owner. That audience was not restated in the interview.

## Product Purpose

Show one local sitting of the oversight desk. A typed question runs through the real `build("local")` pipeline. The page shows the outcome and what each stage did to get there. Success is that a person who does not already know the pipeline can see the path a request took.

## Positioning

The page is the audit of a run. Briefing figures, breach text, tool names, the refused order, and the committee hold come from that run. A neighboring dashboard that recomputes the book and skips the decision trace could not make the same claim.

## Operating Context

The page is served from this repository with `python -m fs_prod_agent.desk`. On this machine it is reached over Wireguard at the host's `wg0` address. With no decider process and no model API key, decisions fall back to the fixture stand-in and the agent follows its script. The book is the quarterly fixture dated 2026-06-30.

## Capabilities and Constraints

- A typed question runs the local pipeline and returns one outcome plus a stage audit.
- The five worked cases stay on the page and open into the same audit.
- The stages are the pipeline stages: context, decide, authorize, execute, observe.
- Domain functions are the source of the briefing and the breach. The page does not recompute them.
- A model signal does not grant permission. Policy returns the verdict.
- An order is refused and does not execute. A committee paper stays in the human queue, with the decider's choice beside the policy verdict.
- `scripts/verify` stays offline. The fixture stand-in is what runs when nothing is listening.
- Do not present live market data, a second checkpoint, or an executed trade.

## Product Principles

- The audit reports the run that just happened, in stage order.
- A typed question and a worked case share one audit.
- The decider's choice and the policy verdict stay visible together.
- The page renders traces. It does not recompute the book.
- Offline fixture behavior is labeled as fixture behavior.
