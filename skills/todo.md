---
title: Walk through pending work
type: skill
updated: 2026-10-06
description: At session start, go through ecosystem/todo with the human — apply, defer or reject.
---

# Skill: todo

Run at session start when `kc todo` reports pending items (it has already created stubs for
files left in `inbox/` and `drafts/`), or whenever the human asks.

1. Show the summary `kc todo` printed (count per kind, titles). Ask: walk through now, or
   **defer everything** (urgent session) — then stop here and start the work.
2. For each item, oldest first, show what it is and what deferring it affects, then:
   - **Apply** — do it with the matching skill: `inbox` → `skills/inbox.md`; `draft` → the
     Route/Reconcile steps of `skills/close.md`; `candidate` → `skills/emergence.md`;
     `adaptation` → `skills/update.md` (B); `task` → as described in the item. Follow the
     *Large tasks* rule in `AGENTS.md`. When done, delete the item file and its processed
     source (keep media — see the `inbox` skill).
   - **Defer** — keep it; if the human gives a reason or a decision, add it to the item body
     and bump `updated`.
   - **Reject** — delete the item and its source (media excepted) and add an entry to
     `ecosystem/decisions.md` saying what was rejected and why.
3. Commit the core (`kc commit-push -m "todo: …"` from the core); it is pushed right away.

Creating items: when you defer a candidate, an adaptation or a large task in any skill, write
an item in `ecosystem/todo/` in the format of `ecosystem/todo/README.md`.
