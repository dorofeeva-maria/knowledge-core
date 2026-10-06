---
title: 0009 — The engine ships no core state; existing repos join with add-module
type: adr
updated: 2026-10-06
---

# 0009. The engine ships no core state; existing repos join with add-module

Status: accepted · 2026-10-06

## Context

The engine shipped `ecosystem/registry.yml`, `templates.yml`, `HOME.md`, `decisions.md` as empty
files that each core then fills. Since the core is rebased onto the engine (ADR 0003), any
engine change to one of them conflicts with the core's content and blocks the core. The
template catalog pointed at a personal SSH URL, which needs keys and leaks a private address
into a public engine. The only way to bring an existing repo into the ecosystem was editing
YAML by hand, and `new-module` refused existing paths — yet migrating means adopting many
existing repos.

## Considered options

State files: keep them in the engine and resolve conflicts in `update` · **the engine ships only
their documentation; `kc bootstrap` creates them in the core** ← chosen.

Template catalog: one shared file · **engine defaults in `config/templates.yml`, the core's own
in `ecosystem/templates.yml`, merged with the core winning** ← chosen.

Existing repos: hand-edit the registry · **`kc add-module`** ← chosen · `add-module` plus a
`kc set` command for every field (deferred — registry fields are edited by hand or by the agent,
and `pull-all` reports mismatches).

## Decision

The engine's `ecosystem/` holds only `README.md` and `todo/README.md`. `kc bootstrap` creates
`registry.yml`, `decisions.md`, `todo/` and `instance.yml` if missing and commits them as an
`auto:` commit. A core is recognized by its layout (`kc/` and `ecosystem/`), not by a state file.
The default catalog lives in `config/templates.yml` with an https URL; `kc templates` and
`kc new-module` read it overlaid by `ecosystem/templates.yml`.

`kc add-module NAME PATH [--external [--write-zone P]...] [--upstream URL] [settings]` registers an
existing repo: `remote` from its `origin`, `upstream` from its `upstream` remote unless given;
it reports contract problems right away (ADR 0008).

## Consequences

- \+ Engine updates never conflict with the core's own state.
- \+ Migration can bring repos in one by one, each prepared first.
- \− `kc` commands before `bootstrap` work on an empty registry.
