---
title: 0003 — One branch, two remotes, rebase sync
type: adr
updated: 2026-10-06
---

# 0003. One branch, two remotes, rebase sync

Status: accepted · 2026-10-06

## Context

The fork model kept a `main` branch mirroring the template and a `working` branch with
content, and rebased `working` onto `upstream main` at every session start. Rebasing rewrites
history that is already pushed to `origin`, so after the first template/engine update the
`--ff-only` pull from origin failed, the next push was rejected, and the other devices could not
fast-forward. `setup.md` said only the first device needs `upstream`, while `bootstrap` wired it
on every device. The local `main` was never updated, so `feature/*` branches were cut from a
stale template. A module's template URL lived only in one device's git config.

## Considered options

Integration method:
- **merge `upstream/main`** — no rewrites, plain push; history gets merge commits.
- **rebase, `upstream` first, then origin** — rebases a stale local copy; the second rebase
  duplicates or conflicts with other devices' commits.
- **rebase, origin first, then `upstream`, then a guarded force-push** ← chosen: linear
  history (template first, content on top), safe across devices.

Branches:
- keep `main` (mirror) + `working` (content) and fast-forward `main` on each sync;
- **one branch `main` with content; the template is only a remote** ← chosen.

When updates apply:
- notify at start, apply on command (can be postponed);
- **always apply at session start; a conflict blocks the repo until it is resolved or the repo
  is detached** ← chosen. Postponing an update is not possible; detaching is.

Template URL storage: the module's own repo (breaks "modules know nothing of the ecosystem") ·
**the registry (`upstream`)** ← chosen.

## Decision

Every repo forked from the engine or a template keeps its content on a single `main` branch,
with remotes `origin` (yours) and `upstream` (engine/template). `kc pull-all` syncs each repo:
fetch → `pull --rebase origin main` (git's fork-point detection recovers from a rewrite pushed
by another device) → `rebase upstream/main`. A clean update is applied and reported as
`UPDATE APPLIED old..new`; the agent then reviews the diff and proposes content adaptation
(`skills/update.md`). A conflicting update is aborted and reported as `UPDATE CONFLICT`; the repo
is blocked until `kc update NAME` resolves it with the human, or `kc detach NAME` (after a
warning) removes the upstream and records `upstream: ~`. git rerere is enabled so a resolution
is remembered.

Pushes use `--force-with-lease` plus an "includes origin" check (the local branch must at some
point have contained origin's tip, per its reflog); git's own `--force-if-includes` rejects
fresh clones, so `kc` performs the equivalent check itself.

The template URL is stored in the registry (`upstream`) and the engine URL in
`ecosystem/instance.yml`; every device restores or removes the remote to match. The core may be
detached from the engine too, with a warning. External repos are only fast-forwarded on their
current branch and never pushed.

## Consequences

- \+ Multi-device sync works after template/engine updates; no branch drifts.
- \+ Linear history: what the template gave vs. what you added is easy to read.
- \+ Losing a device does not lose the link to a template.
- \− History is rewritten on every update; anything outside `kc` that pins commit hashes breaks.
- \− A conflict in a file you rewrote from the template recurs per commit that touched it;
  rerere and the agent mitigate it.
- \− A blocked repo cannot be worked on until resolved or detached.
- \− Templates must publish changes that modules can absorb (see `docs/templates.md`).
