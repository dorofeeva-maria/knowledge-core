# knowledge-core

An engine for a personal ecosystem of independent, version-controlled **modules** — knowledge
bases and processes, each its own git repo — coordinated by one orchestrator, the **core**, and
worked through conversation with [Claude Code](https://claude.com/claude-code).

- You talk; the agent writes what was decided into the right module, as you go.
- Every repo syncs by itself at the start and end of each session started in the core, on every
  device.
- The system notices maintenance — a module that grew, a procedure done by hand three times, a
  format problem — and raises it, so you don't have to remember.
- Each module works on its own: open it alone and its rules and processes are there (sync is then
  yours: pull before, push after — the hooks live in the core).

This repository is the **engine**: copy it once into a private repo — your core — and grow
your ecosystem from there. It holds no personal data.

## Layout

| Path | What |
|------|------|
| `AGENTS.md` | the agent's instructions (`CLAUDE.md` imports it) |
| `kc/` | the orchestrator CLI: registry and git across repos |
| `ecosystem/` | your core's state, created by `kc bootstrap` (see its README) |
| `config/` | the default template catalog, a device `.env` example |
| `docs/` | how it works, setup, templates, decisions (ADRs) |

## Docs

- [`docs/architecture.md`](docs/architecture.md) — pieces, responsibilities, processes.
- [`docs/setup.md`](docs/setup.md) — start an ecosystem, add a device.
- [`docs/templates.md`](docs/templates.md) — module templates.
- [`docs/adr/`](docs/adr/) — why it is built this way; start at
  [ADR 0015](docs/adr/0015-simplified-architecture.md).
- [`CHANGELOG.md`](CHANGELOG.md) — what changed.

## Quickstart

```sh
git clone https://github.com/dorofeeva-maria/knowledge-core my-core && cd my-core
git remote remove origin && gh repo create my-core --private --source . --push
pip install pyyaml
python3 -m kc bootstrap
claude
```

Prerequisites: git, Python 3.9+, PyYAML, Claude Code, GitHub CLI (`gh auth login`).
