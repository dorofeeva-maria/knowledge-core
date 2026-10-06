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
  the ecosystem* plus the engine: the registry, the HOME map, the session log, the candidates
  list, the change journal, and the engine's own ADRs.
- **Module** — an independent git repo (knowledge or project). It knows nothing about the
  ecosystem and nothing about other modules; it can be any shape. It works standalone;
  orchestration is a bonus when a core is present.
- **Tool-package** — not a module: a separate, usually public, reusable package a module
  depends on.
- **Format-template** — a separate repo scaffolding a recurring kind of module; new modules
  are forked from it.
- **Transient** — `inbox/` (raw drops) and `drafts/` (session scratch); gitignored, cleared by `close`.

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
`KC_LANGUAGE`. Instance-wide settings (default `language`) live in committed
`ecosystem/instance.yml`.

## Access & privacy

Every module may be **read** by the core, including private ones. A module is **written**
only to itself; cross-module writes happen only through the core. Privacy is a
*non-surfacing* rule (never expose a private module's specifics in unrelated or public places),
not a read block. The public engine never contains personal content.

## No cross-module links

Links exist only *within* a module, in its own format. Modules never reference each other.
Cross-module relationships, when worth keeping, are a note in the core — not a link in a
file, not a maintained graph. Knowledge moves between modules by distilling it through the
core (a module writing into itself), never by linking. Link-linting is therefore
intra-module only.

## Two layers: mechanics vs judgment

- **Mechanical → `kc` CLI.** Deterministic plumbing (pull, lint, index, registry, commit/push,
  wrapper generation, bootstrap). Any assistant or git hook calls it; it is the source of truth
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
  reviewed via `skills/update.md`); then check `inbox/` and `drafts/` — if anything is pending,
  it must be handled via `close` before new work.
- **During**: a light draft in `drafts/`.
- **`close`** (explicit, interactive, from the core): route knowledge into modules, reconcile
  conflicts (newer `updated` wins; genuine semantic conflicts go to the human), run emergence,
  lint/index touched modules, record a log line + journal, commit per module, push on
  confirmation, clear processed raw (keep media). See `skills/close.md`.
- Closing a session without `close` runs nothing heavy in the background.

## Automation & safety

Automate the read-only / propose side; gate content writes. Mechanical, no-approval actions
(index/HOME regen, intra-module link fixes, `updated` bumps, log line) may run automatically at
session boundaries. Content edits and structural changes (new module, split, extraction) are
proposed; the human decides. There is no background daemon — mechanical work runs at session
start and `close`. A human-readable change journal plus git make every automatic action
auditable and reversible.

## Element lifecycle (emergence)

Elements emerge from sessions and are analyzed at `close` (see `skills/emergence.md`): a
reusable artifact is assessed for extraction into a tool-package *before* it is created; a
theme is promoted to its own module when it has its own process, goal, mass, or recurrence; a
module is split when it stops being legible. The engine itself evolves through ADRs
(`docs/adr/`), written whenever a choice changes its structure, a contract or agent behavior
(see `docs/adr/README.md`).

## Memory

Stable facts about the user live in a separate memory tier, distinct from modules. Conceptually:
episodic (drafts) → semantic (modules) → procedural (rules in `AGENTS.md`).

## Non-goals

Not multi-user / collaborative; not a hosted product; no bespoke GUI or mobile app. The surface
is the terminal and git repos.
