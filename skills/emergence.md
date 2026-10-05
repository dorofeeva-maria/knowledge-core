---
title: Emergence — propose structure changes
type: skill
updated: 2026-10-06
description: Spot when to extract a tool-package, promote a theme to a module, or split a module.
---

# Skill: emergence

Analyze the session and the modules it touched for structure that wants to change. You only
**propose**; the human creates, splits, or retires modules. Record proposals in
`ecosystem/candidates.md` and raise the ripe ones with the human at `close`.

## Reusable artifact (script / command / skill) — assess BEFORE creating it
Decide whether it is specific to this module or useful to other modules / other people;
whether something similar already exists; and whether it should merge into an existing
tool-package. Recommend **extract now / defer / keep in module**. If deferred, create it in
the module and record it in `ecosystem/candidates.md` as pending extraction, then re-raise at
`close`. Tool-packages are separate repos, depended on — they are not modules.

## Promote a theme to its own module
When the theme has its own process/tools, its own goal and life, enough mass, or it recurs
across many sessions.

## Split a module when it stops being legible
- A cluster of recently-worked files alongside many untouched ones → move the active cluster
  to a new module, leave the rest.
- Too many files to hold in your head at once.
- Tangled, over-complex structure.
- Several parts repeat each other's structure → extract a format-template and make each
  repeated part its own module.

## Retire
Propose `frozen` (read-only, keep) or `disconnected` (center stops interacting; the repo
lives on alone) when a module is no longer worked on. The human decides and sets it in the
registry.
