---
title: 0002 — The orchestrator fork is called "core"
type: adr
updated: 2026-10-06
---

# 0002. The orchestrator fork is called "core"

Status: accepted · 2026-10-06

## Context

The project is named knowledge-**core**, while the docs and code called the orchestrator fork
the **center** (`find_center`, `KC_CENTER`, "center-scoped"). Two names for neighbouring ideas
made readers unsure whether "core" meant the engine or the orchestrator.

## Considered options

- **center** — already used everywhere in code and docs; leaves "core" ambiguous.
- **core** — matches the project name; the public template is consistently the **engine**. ← chosen
- **hub** — a neutral third word; adds a term instead of removing one.

## Decision

The private fork that orchestrates the ecosystem is the **core**. The public template it is
forked from is the **engine**. All docs, code and configuration use these two terms:
`KC_CORE` (was `KC_CENTER`), `kc/core.py` (was `kc/center.py`), "core-scoped" commands.

## Consequences

- \+ One term per concept; "core" never means the engine.
- \− Breaking: launchers written by an older `kc bootstrap` export `KC_CENTER`; re-run
  `kc bootstrap` to regenerate them. No compatibility alias is kept (no installed base yet).
- \− "core" is a common word, so `kc check-template` may flag ordinary text that uses it;
  review its hits.
