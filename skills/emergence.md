---
title: Emergence — propose structure changes
type: skill
updated: 2026-10-06
description: Spot when to extract a tool-package, promote a theme to a module, or split a module.
---

# Skill: emergence

Analyze the session and the modules it touched for structure that wants to change. You only
**propose**; the human creates, splits, or retires modules. Record proposals in
`ecosystem/todo/` (`kind: candidate`) and raise the ripe ones with the human at `close`.

## Reusable artifact (script / command / skill) — assess BEFORE creating it
Decide whether it is specific to this module or useful to other modules / other people;
whether something similar already exists; and whether it should merge into an existing
tool-package. Recommend **extract now / defer / keep in module**. If deferred, create it in
the module and record it as a todo item (`kind: candidate`, pending extraction), then re-raise at
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

## Creating a module (only when the human agrees)
When a promotion is accepted, suggest a **template**: read the catalog with `kc templates`,
match the theme to each entry's `when` hint, and recommend one. The human may **accept** it,
decline templates entirely (**own rules** — a bare module), or give **their own template
URL**. Then create it with `kc new-module NAME [--template T | --template-url URL |
--no-template]`. A chosen template becomes the module's `upstream` (fork model, ADR 0003). Never
create a module without the human's go-ahead.

After `kc new-module` (content on `main`): **clarify its purpose and
structure with the user**, then rewrite the template's placeholders (AGENTS.md, README,
starter notes) into the module's real identity and remove any leftover template text. The
module repo must end up with **no ecosystem references** (see `docs/templates.md`). A
format-template extracted from a stabilized module follows the same rules and may carry
type-specific, model-agnostic tooling. Before publishing a template, pass the
`docs/templates.md` checklist: run `kc check-template` (no ecosystem references) and confirm an
assistant could build an adequate module from it standalone.

## Retire
Propose `frozen` (read-only, keep) or `disconnected` (core stops interacting; the repo
lives on alone) when a module is no longer worked on. The human decides and sets it in the
registry.
