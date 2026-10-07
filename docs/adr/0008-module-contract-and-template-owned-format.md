---
title: 0008 — Module contract; format tools belong to templates
type: adr
updated: 2026-10-06
---

# 0008. Module contract; format tools belong to templates

Status: accepted, partly superseded by 0015 · 2026-10-06

## Context

`kc lint` / `kc index` imposed one note format (frontmatter, `[[links]]`, `index.md`) on every
module and the core, although a module "can be any shape"; `close` ran them on every touched
module, writing `index.md` into external and frozen repos too. A module opened alone could not
rebuild its index, since the tool lived in the engine it must not mention. Writes into external
`write_zones` were never committed, while a single `commit-push` there would `git add -A`
anything. Nothing defined what the core expects from a module (branch, remotes), so a module
switched to another branch was silently skipped. Frozen modules without a local copy had no
way to be read.

## Considered options

Format tools: auto-detect the notes format and lint only those modules · lint only modules
flagged in the registry · **the template ships its own tools; the core runs the module's check
command** ← chosen. How the core finds the command: a file-name convention (`tools/check.py`) ·
**a registry field `check`, filled from the template catalog** ← chosen.

Log compaction: keep in the engine · both places · **in the template, with its instructions**
← chosen.

External writes: commit only zone files on the current branch and confirm the push · a
dedicated branch · **never commit: the human commits by the repo's own rules** ← chosen.

Contract check: minimal, every start · **minimal plus the module's format check, every start**
← chosen · a separate on-demand doctor command.

Format problems: block the module · **report and propose fixes** ← chosen.

Frozen without a path: a temporary clone · **read on demand via the web/API** ← chosen.

## Decision

- `kc index`, `kc lint`, `kc check`, `kc compact-log` and the `compact-log` skill are removed
  from the engine. The info template ships `tools/notes.py` (`index`, `check` — read-only,
  including index freshness — and `compact-log`), documented in its `AGENTS.md`.
- The template catalog may declare `check: <command>`; `kc new-module --template` copies it into
  the registry (`--check` sets it by hand). `kc pull-all` runs it in each own module and reports
  `format issues`; `close` runs it for touched modules.
- **Contract** for own modules, checked by `kc pull-all`: branch `main`, `origin` = registry
  `remote`, `upstream` = registry `upstream`, no rebase in progress. A violation is reported as
  `MISMATCH`; the agent proposes to fix it, make the module external, or defer it as a todo item.
  Described in `docs/architecture.md` (*Module contract*).
- `kc commit-push` refuses to run in an external module; the agent lists what it wrote there.
- Frozen modules are never written; without a path they are read via the web/API from `remote`.
- The core itself is not linted.

## Consequences

- \+ Any repo can be a module; format rules apply only where a template brings them.
- \+ A module opened alone keeps its own index and log.
- \+ Branch or remote drift is caught at the next start.
- \− Each template must maintain its own tools; formats can diverge between templates.
- \− The format check runs on every start (one process per module).
