---
title: 0013 — The registry is the map; reconciling always asks; artifacts assessed on creation
type: adr
updated: 2026-10-06
---

# 0013. The registry is the map; reconciling always asks; artifacts assessed on creation

Status: accepted, partly superseded by 0015 · 2026-10-06

## Context

`HOME.md` was generated from the registry plus a line from each module's README, committed, and
could only describe modules present on the current device — so two devices rewrote it back and
forth; beyond that line it duplicated the registry. `kc check-template` scanned templates for
ecosystem words and flagged ordinary text ("docker registry", "core idea"). Reconcile said "the
newer `updated` wins", which does not apply to knowledge from a conversation (no date). The
emergence skill asked to assess a reusable artifact *before* creating it but ran only at `close`,
and gave no path for a module to adopt a template extracted from it.

## Considered options

Map: keep `HOME.md` local-only · **drop it; a `description` field in the registry; `kc registry`
is the map** ← chosen.

check-template: narrow it to exact names · keep it broad · **remove it; the checklist in
`docs/templates.md` is reviewed by reading** ← chosen.

Reconcile: newer wins, ask only on real contradictions · **ask the human about every
discrepancy** ← chosen.

Emergence: **assess artifacts at the moment of creation (rule in `AGENTS.md`), themes and splits
at `close`; to adopt a template, create a new module from it and move the content** ← chosen ·
templates only for new modules.

## Decision

`HOME.md` and `kc home` are removed. The registry has an optional `description`; `new-module` and
`add-module` take `--description` or fill it from the module's README/overview; `kc set` changes
it; `kc registry` prints it. `kc check-template` is removed. `close` asks the human about every
difference between new and recorded knowledge. `AGENTS.md` requires assessing a script, command
or skill before creating it; `skills/emergence.md` describes moving a module onto a new template.

## Consequences

- \+ One source for the module map, identical on every device.
- \+ No silent overwrites of recorded knowledge.
- \− More questions during `close`.
- \− Template hygiene relies on review, not a tool.
