---
title: 0010 — Write on request, one session per core, kc set
type: adr
updated: 2026-10-06
---

# 0010. Write on request, one session per core, kc set

Status: superseded by 0015 · 2026-10-06 · supersedes the "kc set deferred" part of 0009

## Context

With session drafts (ADR 0006), knowledge reaches modules at `close`. A human who says "save
this" expects it saved now. `kc commit-push` commits whole repos and the core tracks one current
session per device, so two sessions in one core would commit each other's changes. Changing a
module's registry fields by hand could leave the repo out of sync (e.g. a new `remote` without
an `origin`).

## Considered options

Writing during a session: always immediately (the agent decides what to write as it goes) ·
only at `close` · **immediately when the human asks, otherwise at `close`; `close` skips what is
already written** ← chosen.

Parallel sessions in one core: support them (explicit file lists for commits, no shared
pointer) · **one session per core at a time, with a warning at start** ← chosen.

Registry edits: by hand, with `pull-all` catching mismatches · **`kc set NAME key=value`, with
side effects and an `auto:` commit** ← chosen.

## Decision

- `AGENTS.md` (*During the session*): on the human's request, write into the module now (Route
  rules) and commit; otherwise the draft carries it to `close`, whose Route step skips what is
  already written.
- One session per core at a time. The session-start hook warns when another session was active
  in the last 30 minutes and has not ended (per-device state in `.kc/`).
- `kc set NAME key=value...` changes `remote`, `status`, `private`, `external`, `write_zones`,
  `language`, `media`, `check` (`~` clears). Setting `remote` points the module's `origin` at it
  and pushes. Templates are changed with `kc detach`, not `set`.

## Consequences

- \+ "Save this" works as expected without waiting for `close`.
- \+ Registry and repos stay in sync through one command.
- \− No parallel sessions in one core; a second one only gets a warning, not a lock.
