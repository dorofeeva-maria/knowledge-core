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
- [`AGENTS.md`](AGENTS.md) — the AI-agnostic instruction entry.

## Layout

| Path | What |
|------|------|
| `kc/` | the mechanical CLI (`kc`) — deterministic plumbing any agent or hook calls |
| `skills/` | AI-agnostic markdown instructions for cognitive operations (`close`, …) |
| `adapters/` | per-AI generators for command wrappers + startup stubs |
| `adr/` | architecture decision records (Nygard) for the engine itself |
| `docs/` | the system canon (architecture, glossary) |
| `ecosystem/` | center state the fork fills in: registry, HOME map, candidates, log, journal |
| `config/` | example instance + device configuration |

Format-templates (scaffolds for new modules) live in **separate repos**, not here.

## Quickstart

> Bootstrap is under construction. The intended flow: fork → `kc bootstrap` → pick your
> AI → the center is set up on this device (clones modules, installs `kc` on PATH,
> generates your AI's wrappers).

## Status

Early scaffold. `kc index|lint|check` operate on a single module. Cross-repo
subcommands and the bootstrap flow are being built incrementally.
