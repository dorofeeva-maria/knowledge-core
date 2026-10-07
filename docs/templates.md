# Authoring a module template

A **template** is a repo with the starting files of a recurring kind of module. `kc new-module
--template T` copies its files into a fresh repo with its own history; the module never hears
from the template again (ADR 0015). The catalog is the engine's `config/templates.yml` plus your
core's `ecosystem/templates.yml`.

## Rules

- **Standalone.** A template's files become the module's files, so they read as a normal repo:
  no mention of the core, the registry, `kc`, or of being a template.
- **`CLAUDE.md` = `@AGENTS.md`.** `AGENTS.md` tells an assistant, working in the module alone,
  how to keep it: note format, folders, links, media, language, how to commit.
- **Placeholders, rewritten on first use.** `AGENTS.md`, `README.md`, starter notes — clearly
  meant to be replaced with the module's real purpose.
- **Links are relative markdown links** (`[text](../concepts/x.md)`), so they work on GitHub and
  in any editor. They never leave the repo.
- **Processes are Claude Code skills**: `.claude/skills/<name>/SKILL.md` with `name` and
  `description` in the frontmatter. A template may ship some; most appear through use.
- **Format tools ship with the template** (e.g. `tools/`), with a read-only check command
  declared in the catalog (`check`); the core runs it at every session start.
- **`.gitignore`** lists what stays on the device (large media, recordings).

## Checklist before publishing

1. No ecosystem references in any file.
2. `AGENTS.md` alone lets an assistant build a sensible module without the core.
3. The template's own files pass its `check`.

## How a template is born

Don't invent one up front. Let a module's shape settle through real work, then copy the common
shape into a template repo and add it to `ecosystem/templates.yml`.
