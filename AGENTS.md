# knowledge-core — agent instructions (canon)

This is the canonical, AI-agnostic instruction entry. **Any** assistant reads this file.
Assistant-specific wrappers (e.g. Claude's `CLAUDE.md` / slash commands) are thin pointers
generated from here by `adapters/`.

## Two layers

- **Mechanical → `kc` CLI.** Deterministic plumbing (sync, commit/push, todo, drafts,
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
| a module's own format check (index, lint) | module | its registry `check` command |
| registry, pull-all, commit-push, push-all, todo | CLI | `kc <cmd>` |
| resolve an update / stop following a template | CLI | `kc update NAME`, `kc detach NAME` |
| map of modules, tags | CLI | `kc registry`, `kc tags [TAG]` |
| create a module / add an existing repo / change its fields / list templates | CLI | `kc new-module`, `kc add-module`, `kc set`, `kc templates` |
| set up this device | CLI | `kc bootstrap` |
| per-AI wrappers | CLI | `kc ensure-wrappers --agent NAME`, `kc add-agent NAME` |

## Session start

Read `ecosystem/memory.md` (facts about the human that hold everywhere). Before working in a
module, read its own `memory.md` if it has one.

The start hook runs `kc pull-all` and `kc todo`. Read their report before anything else:

- `UPDATE CONFLICT` / `REBASE IN PROGRESS` — that repo is **blocked**: do not write to it until
  the update is resolved or the repo is detached. Follow `skills/update.md`.
- `UPDATE APPLIED` — a template/engine update landed; review it with `skills/update.md`.
- `skipped (…)` — the repo was not synced; tell the human why.
- `todo: N pending` — walk through it with `skills/todo.md` (the human may defer all).
- `MISMATCH: …` — a module breaks the contract (branch, remotes): propose to fix it, make it
  external, or defer it as a todo item. `format issues` — propose fixing (not blocking).
- `session: new | continuing` — the session's draft is captured automatically; you do not
  write it. `close` processes it.

Every commit is pushed right away (`kc commit-push`). `kc` never commits in external modules
(the human does), and changes proposed to a template or the engine need confirmation first.

## During the session

- The session draft records the conversation by itself (see *Session start*); `close` routes it
  into modules.
- When the human asks to record, save or update something now, write it into the right module
  right away — same rules as the Route step of `skills/close.md` — and commit it with
  `kc commit-push`. `close` later skips what is already written.
- One session per core at a time: `kc` commits whole repos, so a second session in the same
  core would sweep up the first one's changes. The start hook warns if another session looks
  active.

## Memory

When the human corrects you or states a lasting fact or preference, record it (ADR 0012): if it
belongs to one module's subject, in that module's `memory.md` (create it if the module has no
such file and its format allows); otherwise in `ecosystem/memory.md`. One bullet: the fact,
then **Why:**. Update or remove a fact that turns out wrong; never duplicate one in both places.
Your assistant's built-in memory, if any, is not the source of truth.

## Before creating a script, command or skill

Assess it first with the *Reusable artifact* part of `skills/emergence.md` (keep in module /
extract / defer), right then — not at `close`.

## Large tasks

Before a task that is large — e.g. more than ~20 files, more than one module, or a
template/engine adaptation — state its scale (files/modules touched, a rough token and time
cost) and let the human choose: run it **in the background** (if your assistant can run
background agents, so the session is not blocked), run it **now**, or **defer** it (as an item in
`ecosystem/todo/`). Warn when deferring affects later work.

## Ground rules

- Modules are independent and know nothing of the ecosystem; never add cross-module links —
  related notes share tags instead (`kc tags TAG`, vocabulary in `ecosystem/tags.yml`).
- Privacy: details of a `private` module or a note tagged `private` never go into other modules
  (mention them only in general terms) or into anything public. Private content (the core, a
  `private` module, or any `private`-tagged note) is pushed only to a private GitHub repo; if a
  push refuses (`NOT PUSHED …` because origin is public, non-GitHub, or unverifiable), stop and
  ask the human — never work around it (a work GitLab is not private). (ADR 0014)
- Secrets: never repeat a secret (API key, token, password) back in your replies — acknowledge it
  without echoing the value, so it does not enter the session transcript. `kc` also best-effort
  masks obvious secrets when capturing the draft, but do not rely on that.
- Each piece of knowledge is written into the module it belongs to, in that module's own format.
  Knowledge never moves between modules by copying files or linking: the core re-distills it.
- Propose structural changes (new module, extraction, split) — the human decides.
- Automatic (no approval): mechanical whitelist only. Content edits are gated.
- Sessions run from the **core**; it may write into modules (except `external` ones,
  which are limited to their registry `write_zones`). Opening a module alone is standalone
  mode: follow that module's own rules; ecosystem orchestration is simply absent.
