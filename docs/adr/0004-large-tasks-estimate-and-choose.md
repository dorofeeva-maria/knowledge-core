---
title: 0004 — Large tasks: estimate, then background / now / defer
type: adr
updated: 2026-10-06
---

# 0004. Large tasks: estimate, then background / now / defer

Status: accepted, partly superseded by 0015 (no inbox, engine/template adaptation or assistant-agnostic parts) · 2026-10-06

## Context

Some agent work is long and expensive: adapting content to a template/engine update,
splitting a module, re-routing a big inbox. Run inline, it blocks the human's session and can
consume many tokens without warning. The engine is assistant-agnostic: not every assistant can
run background agents.

## Considered options

- **Always run large tasks in the background** — needs background agents, which not every
  assistant has; hides the cost.
- **Estimate, warn, let the human choose background / now / defer** ← chosen.

## Decision

Before a large task (rule of thumb: more than ~20 files, more than one module, or a
template/engine adaptation) the agent states its scale — files and modules touched, a rough
token and time cost — and offers: run in the background (if the assistant supports it), run
now, or defer. When deferring, it says how that affects further work. The rule lives in
`AGENTS.md` (*Large tasks*) and applies to every skill.

## Consequences

- \+ No surprise blocking or token spend; works with any assistant.
- \− One more confirmation before big jobs.
- Follow-up: deferred tasks need a durable place to wait (pending-work list).
