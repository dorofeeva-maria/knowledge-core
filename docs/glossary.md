# Glossary

- **engine** — this public repo: the template you fork to start an ecosystem (CLI + skills +
  adapters + docs).
- **core** — a fork of the engine; the orchestrator. Holds ecosystem meta-knowledge (registry,
  HOME, todo, decisions) and the engine — never domain knowledge.
- **module** — an independent git repo of knowledge or a project. Self-contained; knows nothing
  of the ecosystem or other modules.
- **external module** — a module with limited access (e.g. a work repo); read it, write only in
  its registry `write_zones`, or not at all.
- **tool-package** — a separate reusable package (not a module) that modules depend on.
- **format-template** — a separate repo scaffolding a recurring kind of module; new modules fork
  from it.
- **registry** — `ecosystem/registry.yml`; canonical module facts, read only by the core.
- **device overlay** — `ecosystem/devices.local.yml` (gitignored); per-device module paths.
- **canon** — the AI-agnostic instructions: `AGENTS.md` + `skills/`.
- **wrapper** — a per-assistant pointer to a skill, generated from the canon by an adapter.
- **adapter** — `adapters/<assistant>/adapter.yml`; how to render wrappers + startup stub for one assistant.
- **skill** — a markdown instruction for a cognitive operation (`close`, `inbox`, `emergence`, `update`, `todo`, `compact-log`).
- **kc** — the mechanical CLI (deterministic plumbing).
- **close** — the session-consolidation skill: route → reconcile → emergence → lint → commit → push → clear.
- **inbox / drafts** — committed raw drop zone / session notes in the core; cleared by `close`; leftovers become todo items.
- **todo** — `ecosystem/todo/`: pending work, one file per item; walked through at session start (`kc todo`, `skills/todo.md`).
- **decisions** — `ecosystem/decisions.md`: decisions about the ecosystem (not the engine).
- **auto commit** — a commit `kc` makes on its own, prefixed `auto:`; the audit trail of automatic actions.
- **status** — a module's lifecycle in the registry: `active`, `frozen` (read-only), `disconnected` (ignored).
- **ADR** — Architecture Decision Record (MADR-lite) for the engine's own evolution: why a choice was made; see `docs/adr/README.md`.
- **fork model** — one branch `main` with your content on top of the template; remotes `origin` (yours) and `upstream` (engine/template); sync = rebase onto origin, then onto upstream (ADR 0003).
- **detach** — stop following a template/engine: `kc detach NAME`; recorded as `upstream: ~`.
