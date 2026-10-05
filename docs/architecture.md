# Architecture

knowledge-core is a model-agnostic engine for a personal ecosystem of independent,
version-controlled **modules** (knowledge bases and projects), coordinated by a central
orchestrator. The input is free-form conversation with an AI assistant; the output is
well-structured, internally-consistent modules — each its own git repo, workable in
isolation, usable with any assistant.

## Pieces

- **Engine** (this repo, public) — skeleton + documentation + the `kc` CLI + skills + adapters.
  You fork it into a center; it never holds personal data.
- **Center** — a fork of the engine. Holds no domain knowledge, only *meta-knowledge about
  the ecosystem* plus the engine: the registry, the HOME map, the session log, the candidates
  list, the change journal, and the engine's own ADRs.
- **Module** — an independent git repo (knowledge or project). It knows nothing about the
  ecosystem and nothing about other modules; it can be any shape. It works standalone;
  orchestration is a bonus when a center is present.
- **Tool-package** — not a module: a separate, usually public, reusable package a module
  depends on.
- **Format-template** — a separate repo scaffolding a recurring kind of module; new modules
  are forked from it.
- **Transient** — `inbox/` (raw drops) and `drafts/` (session scratch); gitignored, cleared by `close`.

There are no module *types* — all modules are equal. The only flag is **external** (a repo
with limited access, e.g. a work repo: read it, write only in declared zones, or not at all).

## Topology & storage

Modules are independent repos; by default new ones sit in `projects/` beside the center, but
they may live anywhere (the center just records each path per device). No submodules, no
nesting. The connective tissue is the center's device-aware registry.

## Fork-from-template model

Applies to every repo created from one of our templates (the center from the engine; modules
from format-templates; tool-packages; templates themselves):

- `main` mirrors the upstream template; it is never polluted with content.
- `working` holds all real content; it is the default working branch.
- At session start, for each such repo: `git pull upstream main --rebase` (rebases `working`
  onto the fresh template) and fast-forwards `main`.
- Improving the template: a `feature/*` branch cut from `main` (generic change only) → PR to
  the upstream template → maintainer merges.
- External / arbitrary repos are exempt: they stay on their own branches; the center adapts to
  whatever they already have.

## Registry, devices, config

The **registry** (`ecosystem/registry.yml`, committed) is read only by the center and holds
the canonical facts it needs even when a module is absent: for each module — `remote`,
`external` (+ `write_zones`), `status` (`active` | `frozen` | `disconnected`), `private`.
See `ecosystem/README.md` for field semantics.

Per-device absolute paths live in a gitignored overlay (`ecosystem/devices.local.yml`), keyed
by device id. `.env` (gitignored) holds `KC_DEVICE_ID` and an optional per-session
`KC_LANGUAGE`. Instance-wide settings (default `language`) live in committed
`ecosystem/instance.yml`.

## Access & privacy

Every module may be **read** by the center, including private ones. A module is **written**
only to itself; cross-module writes happen only through the center. Privacy is a
*non-surfacing* rule (never expose a private module's specifics in unrelated or public places),
not a read block. The public engine never contains personal content.

## No cross-module links

Links exist only *within* a module, in its own format. Modules never reference each other.
Cross-module relationships, when worth keeping, are a note in the center — not a link in a
file, not a maintained graph. Knowledge moves between modules by distilling it through the
center (a module writing into itself), never by linking. Link-linting is therefore
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

- **Start** (hook): for each repo, pull (fork model); then check `inbox/` and `drafts/` — if
  anything is pending, it must be handled via `close` before new work.
- **During**: a light draft in `drafts/`.
- **`close`** (explicit, interactive, from the center): route knowledge into modules, reconcile
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
(`docs/adr/`), written only when a change is proposed back to the engine.

## Memory

Stable facts about the user live in a separate memory tier, distinct from modules. Conceptually:
episodic (drafts) → semantic (modules) → procedural (rules in `AGENTS.md`).

## Non-goals

Not multi-user / collaborative; not a hosted product; no bespoke GUI or mobile app. The surface
is the terminal and git repos.
