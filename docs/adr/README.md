# adr/

Architecture Decision Records for the **engine**: why the engine is built the way it is.
Format: MADR-lite (Nygard's Status · Context · Decision · Consequences plus a mandatory
**Considered options** list) — see `template.md`. Numbered, one decision per file, immutable:
a changed decision is a new ADR whose status supersedes the earlier one (the earlier one's
status line is the only edit allowed: `superseded by NNNN`).

## When a change gets an ADR

Write an ADR when **there were real alternatives** and the choice changes one of:

- the **structure** of the ecosystem (pieces, topology, where data lives, its lifecycle);
- a **contract** — a file format, a folder, a `kc` command or its flags, a config key;
- how an **agent behaves** — what a skill or `AGENTS.md` tells it to do.

No ADR for a fix with no choice in it (a bug, a typo, stale wording): fix it, describe it in the
commit message and in `CHANGELOG.md`.

## Rules

- Written in the engine when the decision is made — in the same commit as the change.
- Generic: they record the engine's design for anyone using the template, never a particular
  user's data or migration history.
- After accepting an ADR, update the docs it affects (see `docs/README.md`) in the same commit;
  the ADR explains *why*, the docs describe *what* and *how*.

## Status at a glance

The current design is described by `docs/architecture.md`; ADR 0015 is the starting point for
why it is this way.

| ADR | Status |
|-----|--------|
| 0001 decision records and doc layers | accepted, partly superseded by 0015 (no skills/adapters layers) |
| 0002 the orchestrator is called core | accepted |
| 0003 single branch, rebase onto upstream | superseded by 0015 |
| 0004 large tasks: estimate and choose | accepted, partly superseded by 0015 |
| 0005 core state: registry, todo, decisions | superseded by 0015 |
| 0006 transcript drafts, push on commit | superseded by 0015 |
| 0007 module settings and media | superseded by 0015 |
| 0008 module contract, template-owned format | accepted, partly superseded by 0015 (no upstream contract) |
| 0009 engine ships no state, add-module | accepted, partly superseded by 0015 |
| 0010 write on request, one session, kc set | superseded by 0015 |
| 0011 shared tags and privacy | accepted, partly superseded by 0015 (no tag vocabulary) |
| 0012 memory in plain files | superseded by 0015 |
| 0013 registry is the map, reconcile asks | accepted, partly superseded by 0015 |
| 0014 private content, private origin | superseded by 0015 (checked once, not per push) |
| 0015 simplified architecture | **accepted** |
