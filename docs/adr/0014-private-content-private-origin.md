---
title: 0014 — Private content is pushed only to a verified-private origin
type: adr
updated: 2026-10-07
---

# 0014. Private content is pushed only to a verified-private origin

Status: superseded by 0015 · 2026-10-07

## Context

The core is private (transcripts, memory, inbox) and so is a module flagged `private` or holding
any `private`-tagged note. Nothing stopped `kc` from pushing them to a public remote: if the setup
step that points `origin` at your own repo is skipped, `origin` stays the public engine and every
auto-commit and transcript lands there. An earlier idea — refuse when `origin` equals `upstream` —
breaks legitimate modules whose upstream is some other (possibly private) repo, and misses a public
`origin` that simply is not the engine. The guard has to hold for background hook pushes too, so it
must live in `kc`, not in an assistant-side tool.

## Considered options

Rule: refuse when origin==upstream · **verify the origin repo's visibility before pushing private
content** ← chosen · an explicit per-repo "origin is private" flag the human sets.

Verifier: **GitHub CLI `gh repo view --json visibility`, installed on every device** ← chosen ·
GitHub REST with a token · an assistant/MCP check (does not cover headless hook pushes). A local
filesystem remote is private by nature; `gh` behaves the same on macOS/Linux/Windows.

Un-queryable origin (no `gh`/auth, or a non-GitHub host): **refuse and explain** ← chosen · trust a
recorded flag · push with a warning. Private content goes only to a private GitHub repo; a
non-GitHub remote (e.g. a work GitLab) is treated as not private.

## Decision

Before `kc` pushes a repo that holds private content — the core always, a module with `private:
true`, or a module with any `private`-tagged note — it inspects `origin`: a local path passes; a
GitHub repo passes only if `gh` reports `private`/`internal`; a public GitHub repo, a non-GitHub
remote, or an origin whose visibility cannot be verified all refuse with `NOT PUSHED — …` and a fix.
`AGENTS.md` tells the assistant to stop and ask the human on such a refusal. `gh` is a bootstrap
prerequisite (`kc bootstrap` reports if it is missing or unauthenticated). The public engine and
template repos are additionally protected on the host: `main` is updated only via pull request.

## Consequences

- \+ Private content cannot reach a public or unverifiable remote, even from a background hook.
- \+ Works across hosts: local paths pass, GitHub is verified, everything else refuses safely.
- \− `gh` must be installed and authenticated or private/core pushes refuse.
- \− Pushing a module costs a scan of its notes for the `private` tag.
