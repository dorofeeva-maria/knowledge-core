# knowledge-core

A model-agnostic engine for a personal ecosystem of independent, version-controlled
**modules** (knowledge bases and projects), coordinated by a central orchestrator.

- **Input** is free-form conversation with an AI assistant.
- **Output** is well-structured, internally-consistent modules — each its own git repo,
  openable and workable in isolation, usable with **any** AI assistant.

This repository is the **engine**: a public template you fork into a private *center*,
from which you grow your ecosystem. It carries only skeleton + documentation + tooling —
never personal data.

## Docs

- [`docs/architecture.md`](docs/architecture.md) — how the ecosystem works (the canon).
- [`docs/glossary.md`](docs/glossary.md) — terms in one place.
- [`docs/templates.md`](docs/templates.md) — how module templates are authored.
- [`AGENTS.md`](AGENTS.md) — the AI-agnostic instruction entry.

## Layout

| Path | What |
|------|------|
| `kc/` | the mechanical CLI (`kc`) — deterministic plumbing any agent or hook calls |
| `skills/` | AI-agnostic markdown instructions for cognitive operations (`close`, …) |
| `adapters/` | per-AI generators for command wrappers + startup stubs |
| `docs/adr/` | architecture decision records (Nygard) for the engine itself |
| `docs/` | the system canon (architecture, glossary) |
| `ecosystem/` | center state the fork fills in: registry, HOME map, candidates, log, journal |
| `config/` | example instance + device configuration |

Format-templates (scaffolds for new modules) live in **separate repos**, not here.

## Quickstart

See [`docs/setup.md`](docs/setup.md) for the full flow. In short: clone this engine as your
center, `git remote rename origin upstream`, run `python3 -m kc bootstrap` (pick language,
device id, assistant), then `kc new-module NAME --template info`. Prerequisites: git, Python
3.9+, `pip install pyyaml`, and a `PATH` dir for the launcher.

## Status

Early scaffold. `kc index|lint|check` operate on a single module. Cross-repo
subcommands and the bootstrap flow are being built incrementally.
