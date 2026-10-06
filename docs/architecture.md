# Architecture

knowledge-core is a model-agnostic engine for a personal ecosystem of independent,
version-controlled **modules** (knowledge bases and projects), coordinated by a central
orchestrator. The input is free-form conversation with an AI assistant; the output is
well-structured, internally-consistent modules — each its own git repo, workable in
isolation, usable with any assistant.

## Pieces

- **Engine** (this repo, public) — skeleton + documentation + the `kc` CLI + skills + adapters.
  You fork it into a core; it never holds personal data.
- **Core** — a fork of the engine. Holds no domain knowledge, only *meta-knowledge about
  the ecosystem* plus the engine: the registry (state of modules and what each holds), the todo list
  (pending work), the decisions log, and the engine's own ADRs. History is the git log.
- **Module** — an independent git repo (knowledge or project). It knows nothing about the
  ecosystem and nothing about other modules; it can be any shape. It works standalone;
  orchestration is a bonus when a core is present.
- **Tool-package** — not a module: a separate, usually public, reusable package a module
  depends on.
- **Format-template** — a separate repo scaffolding a recurring kind of module; new modules
  are forked from it.
- **Transient** — `inbox/` (raw drops) and `drafts/` (session notes); committed in the
  private core so they follow you across devices; cleared by `close`, leftovers become todo
  items.

There are no module *types* — all modules are equal. The only flag is **external** (a repo
with limited access, e.g. a work repo: read it, write only in declared zones, or not at all).

## Topology & storage

Modules are independent repos; by default new ones sit in `projects/` beside the core, but
they may live anywhere (the core just records each path per device). No submodules, no
nesting. The connective tissue is the core's device-aware registry.

## Fork-from-template model

Applies to the core (forked from the engine) and to every module forked from a
format-template (ADR 0003):

- **One branch, `main`,** holds all content. Other branches are ignored by the core.
- **Two remotes:** `origin` — your own repo, shared by your devices; `upstream` — the engine
  or the template. A module's template URL is recorded in the registry (`upstream`), the
  engine's in `ecosystem/instance.yml`, so every device restores the remote.
- **Session start sync** (`kc pull-all`, run by the start hook): fetch → rebase onto
  `origin/main` (other devices' work) → rebase onto `upstream/main` (template/engine updates
  are always applied). History stays linear: the template first, your content on top.
- Because an update rewrites history, pushes use `--force-with-lease` plus an
  "includes origin" check; a device that missed the rewrite recovers with the next sync.
- **An update that conflicts blocks that repo** until resolved (`kc update NAME`, with the
  agent) or until the repo is detached from its template (`kc detach NAME`, warned first).
  After an update is applied, the agent reviews the diff and proposes content adaptation
  (`skills/update.md`). git rerere remembers resolved conflicts.
- Improving the template: a `feature/*` branch cut from `upstream/main` (generic change only) →
  PR to the template → maintainer merges.
- External / arbitrary repos are exempt: the core only fast-forwards their current branch and
  never pushes them.

## Registry, devices, config

The **registry** (`ecosystem/registry.yml`, committed) is read only by the core and holds
the canonical facts it needs even when a module is absent: for each module — `remote`,
`external` (+ `write_zones`), `status` (`active` | `frozen` | `disconnected`), `private`.
See `ecosystem/README.md` for field semantics.

Per-device absolute paths live in a gitignored overlay (`ecosystem/devices.local.yml`), keyed
by device id. `.env` (gitignored) holds `KC_DEVICE_ID` and an optional per-session
`KC_LANGUAGE`. Instance-wide settings (default `language`, draft capture, `large_file_mb`)
live in committed `ecosystem/instance.yml`. Module settings (`language`, `media`) are optional
registry fields, mirrored as plain rules in the module's own `AGENTS.md` (ADR 0007).

## Access & privacy

Every module may be **read** by the core, including private ones. A module is **written**
only to itself; cross-module writes happen only through the core.

Privacy is a *non-surfacing* rule, not a read block (ADR 0011). It applies to a whole module
(registry `private: true`) or to single notes (tag `private`). Their details are never carried
into other modules — mention them only in general terms ("there is a medical context") — and
never into anything public (the engine, templates, published pages, a CV). The public engine
never contains personal content.

## No cross-module links

Links exist only *within* a module, in its own format. Modules never reference each other.
Cross-module relationships are expressed by **shared tags**: notes carry `tags: [...]` in
their frontmatter, the core keeps the vocabulary (`ecosystem/tags.yml`) and finds related notes
in any module with `kc tags TAG` (ADR 0011). A tag reads naturally in a module detached from
the ecosystem. Knowledge moves between modules by distilling it through the
core (a module writing into itself), never by linking. Link checking, where a module's
format has one, is intra-module only.

## Module contract

What the core expects of a module, so it can work with any repo (ADR 0008):

- **Every module:** a git repo at the path recorded for this device. Nothing about its
  content or format is required; settings in the registry are optional.
- **Own modules** (not external): branch `main`; `origin` = registry `remote`; `upstream` =
  registry `upstream`; no rebase left in progress. Checked by `kc pull-all` on every start; a
  violation is reported as `MISMATCH` and the agent proposes to fix it, make the module
  external, or defer it. Other branches are ignored.
- **Format:** a module's format tools (index, lint, log compaction) ship with its template;
  its registry `check` command (taken from the template catalog) runs on every start and in
  `close`. Problems are reported, not blocking.
- **External modules:** read; written only in `write_zones`; never committed, pushed or
  rebased by `kc` — the human commits by that repo's rules.
- **Frozen modules:** read only; never written. Without a local path they are read on demand
  from their `remote` (web/API, e.g. `gh api` or raw file URLs).

## Two layers: mechanics vs judgment

- **Mechanical → `kc` CLI.** Deterministic plumbing (sync, registry, commit/push, todo,
  session drafts, wrapper generation, bootstrap). Any assistant or git hook calls it; it is the source of truth
  for mechanics. See `kc/`.
- **Cognitive → skills.** Judgment-based operations are AI-agnostic markdown instructions in
  `skills/`. An assistant follows the relevant skill, which tells it when to call `kc`.

## AI-agnostic instructions

`AGENTS.md` is the canonical entry every assistant reads. Per-assistant wrappers (e.g. Claude's
`CLAUDE.md` and slash commands) are thin pointers generated from the canon by `adapters/`. Each
assistant's session-start stub re-runs `kc ensure-wrappers`, so wrappers regenerate from the
canon on every start and never drift. Generated wrappers are gitignored. An assistant without
an adapter still works via `AGENTS.md` (the universal fallback).

## Session lifecycle

- **Start** (hook): sync every repo (fork model above; template/engine updates are applied and
  reviewed via `skills/update.md`); then `kc todo` stubs leftover `inbox/`/`drafts/` files and
  lists all pending work, which the agent walks through with the human — apply, defer or
  reject each item, or defer everything (`skills/todo.md`).
- **During**: the session's draft `drafts/<date>-<session8>.md` is a raw transcript (the
  human's messages and the assistant's replies) that `kc` appends in the background every
  5 turns or 15 minutes, before compaction and at session end — committed and pushed each
  time. A draft exists ⇔ its session has unprocessed content; on resume the same draft
  continues (ADR 0006).
- **`close`** (explicit, interactive, from the core): route knowledge into modules, reconcile
  conflicts (newer `updated` wins; genuine semantic conflicts go to the human), run emergence,
  run touched modules' checks, record decisions and todo items, commit and push per module
  (external modules only after confirmation), delete the processed draft and raw (keep
  media). See `skills/close.md`.
- Ending a session without `close`: the end hook saves the rest of the transcript and warns;
  the draft becomes a todo item at the next start.

## Automation & safety

Automate the read-only / propose side; gate content writes. Mechanical, no-approval actions
(index regeneration, intra-module link fixes, `updated` bumps, todo stubs) may run automatically at
session boundaries. Content edits and structural changes (new module, split, extraction) are
proposed; the human decides. There is no background daemon — mechanical work runs at session
start and `close`. Every change `kc` makes on its own is a separate commit prefixed `auto:`, so
automatic actions are auditable (`git log --grep '^auto:'`) and reversible (`git revert`).

## Element lifecycle (emergence)

Elements emerge from sessions and are analyzed at `close` (see `skills/emergence.md`): a
reusable artifact is assessed for extraction into a tool-package *before* it is created; a
theme is promoted to its own module when it has its own process, goal, mass, or recurrence; a
module is split when it stops being legible. The engine itself evolves through ADRs
(`docs/adr/`), written whenever a choice changes its structure, a contract or agent behavior
(see `docs/adr/README.md`).

## Memory

Stable facts about the human and corrections to the assistant live in plain files any
assistant reads (ADR 0012): `ecosystem/memory.md` in the core for facts that hold everywhere,
and a module's own `memory.md` for facts that belong to its subject (e.g. "cite sources in APA
style" belongs to a research module). Before writing a fact, the agent decides which
module it belongs to; the core gets only what fits no module. An assistant's built-in memory is
at most a cache. Conceptually: episodic (session drafts) → semantic (modules) → procedural
(`AGENTS.md`, skills, module instructions) → memory (core and module `memory.md`).

## Non-goals

Not multi-user / collaborative; not a hosted product; no bespoke GUI or mobile app. The surface
is the terminal and git repos.
