# Glossary

- **engine** — this public repo: the template you fork to start an ecosystem (CLI + skills +
  adapters + docs).
- **center** — a fork of the engine; the orchestrator. Holds ecosystem meta-knowledge (registry,
  HOME, log, candidates, journal) and the engine — never domain knowledge.
- **module** — an independent git repo of knowledge or a project. Self-contained; knows nothing
  of the ecosystem or other modules.
- **external module** — a module with limited access (e.g. a work repo); read it, write only in
  its registry `write_zones`, or not at all.
- **tool-package** — a separate reusable package (not a module) that modules depend on.
- **format-template** — a separate repo scaffolding a recurring kind of module; new modules fork
  from it.
- **registry** — `ecosystem/registry.yml`; canonical module facts, read only by the center.
- **device overlay** — `ecosystem/devices.local.yml` (gitignored); per-device module paths.
- **canon** — the AI-agnostic instructions: `AGENTS.md` + `skills/`.
- **wrapper** — a per-assistant pointer to a skill, generated from the canon by an adapter.
- **adapter** — `adapters/<assistant>/adapter.yml`; how to render wrappers + startup stub for one assistant.
- **skill** — a markdown instruction for a cognitive operation (`close`, `inbox`, `emergence`).
- **kc** — the mechanical CLI (deterministic plumbing).
- **close** — the session-consolidation skill: route → reconcile → emergence → lint → commit → push → clear.
- **inbox / drafts** — gitignored raw drop zone / session scratch; cleared by `close`.
- **status** — a module's lifecycle in the registry: `active`, `frozen` (read-only), `disconnected` (ignored).
- **ADR** — Architecture Decision Record for the engine's own evolution; written only on a PR to the engine.
- **fork model** — `main` mirrors the upstream template, `working` holds content; start pulls `upstream main --rebase`.
