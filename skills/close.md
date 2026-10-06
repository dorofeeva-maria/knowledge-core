---
title: Close a session
type: skill
updated: 2026-10-06
description: Consolidate the session — route its draft into modules, reconcile, check, commit and push.
---

# Skill: close

Run at the end of a working session, from the **core** (the repo with `kc/` and
`ecosystem/`). You consolidate everything the session produced into the right
modules, keep the base consistent, and record what happened. You make the judgments and ask
the human; you call `kc` for every mechanical/deterministic step — never reimplement it.

## Before you start
- Run `kc registry` to see the modules, what each one holds (description), their `status`,
  flags, and which are present on this device. It is the map for routing.
- Run `kc draft` to flush the rest of the conversation into this session's draft.
- Gather the session's material: this session's draft (`drafts/*-<session8>.md`, a raw
  transcript), everything in `inbox/` (see the `inbox` skill), and other leftovers the human
  chose to process now (`skills/todo.md`).

## Steps

1. **Route.** Skip what was already written during the session at the human's request. For
   each other distinct piece of knowledge, decide which module it belongs to (one
   topic per note) and write it **into that module's own repo**, in that module's format and
   following that module's own rules if it has any (read its `AGENTS.md` / `README`).
   - Prefer updating an existing note over creating a near-duplicate; bump its `updated`.
   - Tags: if the module's notes use `tags`, tag cross-cutting entities (people, places, stack,
     level, `private`) — not the folder or type. Use tags from `ecosystem/tags.yml`; add a new
     one there with a one-line meaning. Run `kc tags TAG` to see related notes in other modules
     and stay consistent with them (reconcile as in step 2, without linking).
   - Privacy: never carry details of a `private` module or a note tagged `private` into
     another module — a general mention only. Tag a note `private` when it holds personal
     material (health, family, finances, other people's private messages).
   - Never write cross-module links. Never write into a `frozen` module. Never write into an
     `external` module outside its `write_zones`; with no zones, treat it as read-only. `kc`
     never commits in an external module: list what you wrote there so the human commits it
     by that repo's rules.
   - Language: the module's registry `language` if set, else the session language
     (`KC_LANGUAGE` in `.env`, else instance `language`). Media: as in the `inbox` skill.
   - If the module's `AGENTS.md` states a different language or media rule than the registry,
     point it out and propose to sync them.

2. **Reconcile.** Whenever new knowledge differs from what a module already says — an update,
   a contradiction, or two notes that disagree — **ask the human** (with your assistant's
   question tool if it has one), showing both versions with their sources and dates. Never pick
   silently. Apply the answer; when a fact is replaced, keep the old value with its period
   ("until 2026-10: …") if history matters.

3. **Emergence.** Apply the `emergence` skill: spot a theme ripe for its own module, a
   reusable artifact to extract into a tool-package, or a module that should split. Record
   proposals as todo items (`kind: candidate`) and raise the ripe ones with the human. **Propose
   only — never create or delete modules yourself.**

4. **Module checks.** In each module you touched, follow its own `AGENTS.md` for index and
   format upkeep (e.g. rebuild its index), then run its registry `check` command if it has
   one, from the module's root; fix what it reports (mechanical fixes right away, content
   fixes with the human). If a module's purpose changed, update its registry description
   (`kc set NAME description="…"`).

5. **Record.** Add decisions about the ecosystem taken this session (module created, split,
   frozen or detached; a pending item rejected; a choice between real alternatives) to
   `ecosystem/decisions.md`. Everything you deferred is a todo item (`skills/todo.md`). The
   rest of the history is the commits. Decisions about the **engine itself** become an ADR in
   the engine (see `docs/adr/README.md`).

6. **Commit (per module).** In each touched repo (and the core) run
   `kc commit-push -m "<message>"` from that repo — a message describing what changed **in
   that module**, honoring the module's own commit conventions if any. It pushes right away
   (ADR 0006). External modules are not committed by `kc`: list the files you wrote there for
   the human. Show the combined report.

7. **Clear.** Delete this session's draft and the inbox items you processed, and their todo
   items if any; commit the core. Media originals have moved into modules (`inbox` skill).
   Anything unresolved stays and becomes a todo item; say so. If the
   conversation goes on after `close`, a new draft starts by itself from this point.

## Rules
- Mechanical steps go through `kc`; cognitive judgment is yours.
- You are interactive here: content is written with the human present; structural changes,
  pushes of external modules and changes proposed to a template or the engine need explicit
  confirmation. Everything else is pushed on commit.
- Leftover drafts/inbox become todo items at the next session start (`kc todo`).
