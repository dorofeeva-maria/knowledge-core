---
title: 0015 — Simplified architecture
type: adr
updated: 2026-10-07
---

# 0015. Simplified architecture: one owner per responsibility

Status: accepted · 2026-10-07 · supersedes 0003, 0005, 0006, 0007, 0010, 0012, 0014; partly
0001, 0008, 0009, 0011, 0013

## Context

Within two days the engine had grown to ~1900 lines of `kc`, 14 ADRs and ~60 open findings from
blind review. Most findings were the cost of mechanisms the engine had chosen for itself, not of
the problem it solves: rebasing every repo onto engine and template updates (force-push,
blocked repos, conflicts in every module at once), capturing raw transcripts in the background
(races, a tail left by every `close`, secrets in git), adapters for any assistant, an inbox with
large-file rules. Responsibilities had blurred: `kc` held about ten (sync, transcripts, privacy
policy, large files, todo, tags, wrappers, bootstrap…), `close` seven steps, the hooks did
network writes and rewrote history.

The actual requirements: one person, two devices, Claude Code only; modules as separate repos
(knowledge and processes), each usable alone; a center that can read, write and run any
module's processes; nothing depends on remembering to commit; maintenance the human does not
want to do must be started by the system; the engine stays public as an artifact, while the
personal core lives on its own.

## Considered options

Each part was decided between alternatives:

- **Updates:** rebase core and modules onto engine/template updates — vs **a copy, no update
  channel**. ← chosen for both the engine and templates.
- **Source of knowledge:** raw transcripts processed by `close` / an agent-kept session digest /
  a pointer to unsaved sessions — vs **the agent writes into modules at once**. ← chosen
- **Sync:** report only / OS timer — vs **hooks at session start and end: commit → rebase onto
  origin → push, no force**. ← chosen
- **kc:** one CLI with internal packages / no CLI — vs **kc is only the orchestrator: registry +
  git across repos + module creation + bootstrap + signals**. ← chosen
- **close:** a thin close / three skills on request — vs **no close; the system starts
  maintenance itself**: signals at start (kc) and rules during work (agent). ← chosen
  (A Stop-hook nudge was rejected.)
- **Module processes from the core:** generated wrappers / `--add-dir` — vs **the agent finds
  a module's skill through the registry and follows it**; kc lists skills in `kc registry`. ← chosen
- **Inbox:** keep a drop folder — vs **none: files arrive as paths in the chat**. ← chosen
- **Privacy check:** on every push / none — vs **once, when a repo gets its remote and at
  bootstrap**. ← chosen
- **Links:** `[[wikilinks]]` — vs **relative markdown links** (work on GitHub and in any
  editor; Obsidian is not used). ← chosen
- **Tags:** a shared vocabulary with `kc tags` — vs **tags without a vocabulary, found by
  grep**. ← chosen
- **State:** a folder of todo items, memory in core and modules — vs **one `todo.md`, one
  `memory.md` in the core**; module rules live in the module's `AGENTS.md`. ← chosen
- **External repos:** write zones — vs **read only**. ← chosen
- **Statuses:** active / frozen / disconnected — vs **active / frozen**. ← chosen

## Decision

We will build the engine around one owner per responsibility:

- **Engine** — copied once into a private core; no upstream remote, no updates. Changes to the
  engine later will be decided when needed.
- **Template** — its files are copied into a fresh repo; no link back.
- **kc** — `bootstrap`, `registry`, `templates`, `new-module`, `add-module`, `set`, `reviewed`,
  `sync`, `status`, `hook start|end`. It never reads meaning out of content.
- **Hooks** (Claude Code, installed per device in `.claude/settings.local.json` with the
  absolute Python path) — `SessionStart`: `kc sync` + signals; `SessionEnd`: `kc sync`.
- **Sync** — per repo: commit leftovers → fetch → rebase onto `origin/main` → push. No force,
  no rewriting of pushed history; a conflict stops that repo only. Frozen: fast-forward only.
  External: fast-forward on its own branch when clean, never committed.
- **Signals** — `format:` (module check failed), `structure:` (growth since `kc reviewed`),
  `repeat:` (a manual procedure at 3× in `todo.md`), `todo open:`.
- **Agent** (`AGENTS.md`) — writes into modules as things are decided, reconciles while
  writing, commits with meaningful messages, raises signals at session start, notices growth
  and repeats during work, proposes structure. Claude's built-in memory is off in the core.
- **Module** — `CLAUDE.md` (`@AGENTS.md`), its rules, its processes as
  `.claude/skills/<name>/SKILL.md`, its format tools and `.gitignore` (large or device-only files).
- **Registry fields** — `description`, `remote`, `status` (active | frozen), `private`,
  `external`, `check`, `reviewed`. Removed: `upstream`, `write_zones`, `language`, `media`
  (language and media are rules in the module's `AGENTS.md`, one place).
- **Core state** — `registry.yml`, `memory.md`, `todo.md`, `decisions.md`, `instance.yml`.

Removed: `kc pull-all|commit-push|push-all|update|detach|draft|todo|tags|ensure-wrappers|
add-agent`, the launcher, `adapters/`, `skills/` (close, inbox, emergence, todo, update),
`drafts/`, `inbox/`, `ecosystem/todo/`, `tags.yml`, the large-file policy, secret masking, the
one-session warning.

## Consequences

- \+ Each piece has one sentence of responsibility; `kc` is about half its former size.
- \+ No history rewriting and no force-push: the A-group findings (upstream rebase), the
  B-group (transcripts), D (inbox, large files) and most of E disappear with their mechanisms.
- \+ Sync no longer depends on the human's memory.
- \− What the agent does not write during a session is lost; the agent's discipline is the
  only safeguard. If losses show up in practice, add a pointer to unsaved sessions.
- \− The end hook may not run (a killed terminal); the start hook commits the leftovers, with an
  `auto:` message.
- \− Cores never receive engine fixes; a fix is ported by hand if wanted.
- \− Only Claude Code is supported; another assistant can still read `AGENTS.md`, without hooks.
