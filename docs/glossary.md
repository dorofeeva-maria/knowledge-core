# Glossary

- **engine** — this public repo; you copy it once to start your core.
- **core** — your private copy of the engine; the orchestrator. Holds the registry, memory,
  todo and decisions — never subject knowledge.
- **module** — an independent git repo with its own subject, rules, processes and tools.
- **external module** — a repo that is not yours (e.g. a work repo): read only, never committed.
- **frozen** — a module of yours whose subject is closed: read only, pulled, no signals.
- **private** — a module with personal content: its remote must be private.
- **template** — a repo whose files a new module starts from; no link afterwards.
- **process** — a module's Claude Code skill, `.claude/skills/<name>/SKILL.md`.
- **registry** — `ecosystem/registry.yml`: the map of modules.
- **device overlay** — `ecosystem/devices.local.yml` (gitignored): where modules live on this device.
- **kc** — the core's CLI: registry and git across repos.
- **sync** — commit leftovers, rebase onto origin, push; run by the hooks at session start and end.
- **signal** — a fact kc reports at session start for the agent to raise: `format:`,
  `structure:`, `repeat:`, `todo open:`.
- **review** — looking at a module's structure; `kc reviewed NAME` records it.
- **memory** — `ecosystem/memory.md`: lasting facts about the human.
- **todo** — `ecosystem/todo.md`: tasks, candidates, repeats.
- **decisions** — `ecosystem/decisions.md`: decisions about the ecosystem (engine decisions are ADRs).
- **ADR** — Architecture Decision Record for the engine (`docs/adr/`).
