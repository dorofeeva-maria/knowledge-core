# knowledge-core — agent instructions (canon)

This is the canonical, AI-agnostic instruction entry. **Any** assistant reads this file.
Assistant-specific wrappers (e.g. Claude's `CLAUDE.md` / slash commands) are thin pointers
generated from here by `adapters/`.

## Two layers

- **Mechanical → `kc` CLI.** Deterministic plumbing (lint, index, pull, commit/push,
  registry, wrapper generation). Call it; don't reimplement it. See `kc/`.
- **Cognitive → skills.** Judgment-based operations are markdown instructions in `skills/`.
  Follow the relevant skill; it tells you when to call `kc`.

## Operations

| Operation | Layer | Where |
|-----------|-------|-------|
| close a session (route knowledge, reconcile, commit, push) | skill | `skills/close.md` |
| process inbox / raw drop | skill | `skills/inbox.md` |
| emergence (propose module / extraction / split) | skill | `skills/emergence.md` |
| apply a template/engine update, adapt content | skill | `skills/update.md` |
| walk through pending work (todo) | skill | `skills/todo.md` |
| index, lint, check | CLI | `kc index\|lint\|check` |
| registry, pull-all, commit-push, push-all, todo | CLI | `kc <cmd>` |
| resolve an update / stop following a template | CLI | `kc update NAME`, `kc detach NAME` |
| HOME map, compact-log, check-template | CLI | `kc home`, `kc compact-log`, `kc check-template` |
| create a module / list templates | CLI | `kc new-module`, `kc templates` |
| set up this device | CLI | `kc bootstrap` |
| per-AI wrappers | CLI | `kc ensure-wrappers --agent NAME`, `kc add-agent NAME` |

## Session start

The start hook runs `kc pull-all` and `kc todo`. Read their report before anything else:

- `UPDATE CONFLICT` / `REBASE IN PROGRESS` — that repo is **blocked**: do not write to it until
  the update is resolved or the repo is detached. Follow `skills/update.md`.
- `UPDATE APPLIED` — a template/engine update landed; review it with `skills/update.md`.
- `skipped (…)` — the repo was not synced; tell the human why.
- `todo: N pending` — walk through it with `skills/todo.md` (the human may defer all).
- `session: new | continuing` — the session's draft is captured automatically; you do not
  write it. `close` processes it.

Every commit is pushed right away (`kc commit-push`), except external modules (confirm, then
`kc push-external NAME`) and changes proposed to a template or the engine (confirm first).

## Large tasks

Before a task that is large — e.g. more than ~20 files, more than one module, or a
template/engine adaptation — state its scale (files/modules touched, a rough token and time
cost) and let the human choose: run it **in the background** (if your assistant can run
background agents, so the session is not blocked), run it **now**, or **defer** it (as an item in
`ecosystem/todo/`). Warn when deferring affects later work.

## Ground rules

- Modules are independent and know nothing of the ecosystem; never add cross-module links.
- Write only within the current module; cross-module moves happen through the core.
- Propose structural changes (new module, extraction, split) — the human decides.
- Automatic (no approval): mechanical whitelist only. Content edits are gated.
- Sessions run from the **core**; it may write into modules (except `external` ones,
  which are limited to their registry `write_zones`). Opening a module alone is standalone
  mode: follow that module's own rules; ecosystem orchestration is simply absent.
