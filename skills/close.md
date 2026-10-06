---
title: Close a session
type: skill
updated: 2026-10-06
description: Consolidate the session — route knowledge into modules, reconcile, lint, commit, push.
---

# Skill: close

Run at the end of a working session, from the **core** (a repo with
`ecosystem/registry.yml`). You consolidate everything the session produced into the right
modules, keep the base consistent, and record what happened. You make the judgments and ask
the human; you call `kc` for every mechanical/deterministic step — never reimplement it.

## Before you start
- Run `kc registry` to see the modules, their `status`, `external` flag + write zones, and
  which are present on this device.
- Gather the session's material: everything in `drafts/`, everything in `inbox/` (see the
  `inbox` skill), and the conversation so far.

## Steps

1. **Route.** For each distinct piece of knowledge, decide which module it belongs to (one
   topic per note) and write it **into that module's own repo**, in that module's format and
   following that module's own rules if it has any (read its `AGENTS.md` / `README`).
   - Prefer updating an existing note over creating a near-duplicate; bump its `updated`.
   - Never write cross-module links. Never write into an `external` module outside its
     `write_zones`; with no zones, treat it as read-only.
   - Language: the module's own setting if it has one, else the session language
     (`KC_LANGUAGE` in `.env`, else instance `language`).

2. **Reconcile.** When new knowledge conflicts with what a module already says: if both notes
   carry `updated` dates and one is clearly newer, the newer wins — note the change. If it is
   a genuine semantic conflict with no clear winner, **stop and ask the human**; never pick
   silently.

3. **Emergence.** Apply the `emergence` skill: spot a theme ripe for its own module, a
   reusable artifact to extract into a tool-package, or a module that should split. Record
   proposals as todo items (`kind: candidate`) and raise the ripe ones with the human. **Propose
   only — never create or delete modules yourself.**

4. **Lint & index.** For each module you touched (and the core), run `kc lint <path>` and
   `kc index <path>`; fix broken intra-module links and stale indexes. Regenerate the
   core's `HOME.md` with `kc home` if the set of modules changed.

5. **Record.** Add decisions about the ecosystem taken this session (module created, split,
   frozen or detached; a pending item rejected; a choice between real alternatives) to
   `ecosystem/decisions.md`. Everything you deferred is a todo item (`skills/todo.md`). The
   rest of the history is the commits. Decisions about the **engine itself** become an ADR in
   the engine (see `docs/adr/README.md`).

6. **Commit (per module).** In each touched repo (and the core) run
   `kc commit-push -m "<message>"` — a message describing what changed **in that module**,
   honoring the module's own commit conventions if any. Do not push yet. Show the human the
   combined report.

7. **Push.** Ask the human to confirm, showing the commits. On yes, run `kc push-all`.

8. **Clear.** Delete the drafts and inbox items you processed, and their todo items if any.
   **Keep media originals and their transcripts** — do not delete media. Anything unresolved
   stays and becomes a todo item; say so.

## Rules
- Mechanical steps go through `kc`; cognitive judgment is yours.
- You are interactive here: content is written with the human present; structural changes and
  the push need explicit confirmation.
- Leftover drafts/inbox become todo items at the next session start (`kc todo`).
