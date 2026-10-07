---
title: 0005 — Core state: registry, todo, decisions; history is git
type: adr
updated: 2026-10-06
---

# 0005. Core state: registry, todo, decisions; history is git

Status: superseded by 0015 · 2026-10-06

## Context

The core kept four state files: `registry.yml` (which modules exist), `log.md` (a line per
`close`), `journal.md` (what automatic actions did) and `candidates.md` (proposed extractions).
`log`, `journal` and the git history described the same events at different detail; `kc` never
wrote the journal although it changes core files itself (`new-module`, `detach`, `home`). Work
that was deferred — unprocessed inbox/drafts, candidates, content to adapt after a template
update, large tasks — had no common place, and `inbox/`/`drafts/` were gitignored, so they lived
on one device only.

## Considered options

State files:
- keep all four and sharpen their boundaries, plus a todo list;
- registry + todo + one human log that `kc` and `close` both append to;
- **registry (state) + `todo/` (pending work) + `decisions.md` (ecosystem decisions); history is
  git, automatic actions are commits prefixed `auto:`** ← chosen.

Todo shape: one `todo.md` list (merge conflicts across devices) · **one file per item with
frontmatter** ← chosen. Items for inbox/drafts: derived on the fly · **a stub file per
leftover raw file** ← chosen. Walk-through at start: one by one always · summary only ·
**summary, then walk through now or defer all** ← chosen. Repeatedly deferred items: no
escalation.

Decisions: a folder of MADR-lite files · **one `decisions.md`, an entry per decision, newest
first** ← chosen.

inbox/drafts: device-local · **committed in the private core** ← chosen.

## Decision

The core's state is `ecosystem/registry.yml`, `ecosystem/HOME.md` (generated),
`ecosystem/todo/` and `ecosystem/decisions.md`. `log.md`, `journal.md` and `candidates.md` are
removed; candidates become todo items (`kind: candidate`).

`kc todo` (run by the start hook) creates a stub item for every file in `inbox/` or `drafts/`
that has none — those were not processed by `close` — and prints a summary. The agent offers to
walk through it (`skills/todo.md`): apply, defer, or reject each item, or defer everything.
Applying deletes the item and its source; rejecting also records the reason in
`decisions.md`. Skills write items for whatever they defer.

Every command that changes core files on its own (`new-module`, `detach`, `home`, `bootstrap`,
`todo`) commits only those files with a message prefixed `auto:`.

`inbox/` and `drafts/` are committed.

## Consequences

- \+ One place for pending work, visible on every device; nothing deferred is forgotten.
- \+ Automatic actions are auditable and revertible without a hand-kept journal.
- \− The core must stay private: it now holds raw material and drafts.
- \− Large media in `inbox/` grows the core's history — where media lives long-term is open.
