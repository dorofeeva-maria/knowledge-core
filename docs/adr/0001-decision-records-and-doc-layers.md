---
title: 0001 — Decision records (MADR-lite) and documentation layers
type: adr
updated: 2026-10-06
---

# 0001. Decision records (MADR-lite) and documentation layers

Status: accepted · 2026-10-06

## Context

The engine had an ADR folder (Nygard format) but no ADRs, and its design decisions were mixed
into `architecture.md`. ADRs were to be written "only when opening a PR to the engine", so
decisions made while building the engine had no record. A reader — human or a fresh agent with
no prior context — could not tell which alternatives had already been weighed, nor which file is
authoritative for a given fact.

## Considered options

- **Nygard** — Status / Context / Decision / Consequences; short, but rejected alternatives
  live only in free prose and get lost.
- **MADR-lite** — Nygard plus a mandatory *Considered options* list. ← chosen
- **MADR full** — adds decision drivers, per-option pros/cons, confirmation; too heavy for most
  engine decisions.
- **Y-statements in one file** — one sentence per decision; too thin for decisions with several
  moving parts.

For the threshold: an ADR for every change (drowns the important ones) · only for "architectural"
changes (misses agent-behavior and contract changes) · **when a choice between real alternatives
changes structure, a contract, or agent behavior** ← chosen.

For the rest of the docs: keep as is · full Diátaxis folders · **three layers — agent
instructions, human docs split by Diátaxis type, decisions** ← chosen.

## Decision

We record engine decisions as MADR-lite ADRs in `docs/adr/`, one per decision, whenever a choice
between real alternatives changes the ecosystem's structure, a contract (file, folder, command,
config key), or agent behavior. Fixes without a choice go to the commit message and
`CHANGELOG.md`. ADRs are written when the decision is made, not only on a PR.

Documentation is split into layers (`docs/README.md`): instructions for agents (`AGENTS.md`,
`skills/`), explanation / how-to / reference for humans, decisions (`docs/adr/`), changes
(`CHANGELOG.md`). Each fact lives in one place.

## Consequences

- \+ A blind reviewer sees which alternatives were already rejected and why.
- \+ Clear home for every kind of text; less duplication between docs and skills.
- \− Every accepted ADR must be accompanied by doc updates in the same commit.
