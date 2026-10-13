# Authoring a module template

A **template** is a repo with the starting files of a recurring kind of module. `kc new-module
--template T` copies its files into a fresh repo with its own history. The files the template
**owns** (`owned` in its catalog entry: skills, shared assets, format tools) are later refreshed
in every module made from it by `kc template-update`, file by file; everything else is the
module's (ADR 0016). The catalog is the engine's `config/templates.yml` plus your
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

## Changing a template

1. In the template's local clone: `git checkout main` and `git pull` first — templates are
   released only from `main`, and `kc template-update` reads only `main`. Edit, run its `check`,
   commit, push.
2. Make sure its catalog entry's `owned` covers the files you changed that belong to the
   template's machinery. Content files (notes, `AGENTS.md`) are never owned.
3. `kc template-update T --dry-run`: what each module gets; "KEPT LOCAL" = a module changed that
   file itself and the template changed it too — bring the template's change in by hand. Then
   `kc template-update T` (add `--diff` to see changes to files it doesn't own, like `AGENTS.md`,
   and carry them over by hand where they fit). A module with KEPT LOCAL or NAME CLASH files
   keeps its recorded version until they are resolved, so they show up again on every run; a
   KEPT LOCAL file merged together with edits of the module's own can't be recognised as merged —
   record it with `kc template-bind NAME T --version SHA`.
4. `kc sync` pushes the module commits.

A module made before `template` was recorded: `kc template-bind NAME T` finds the closest
template commit and records it.

## How a template is born

Don't invent one up front. Let a module's shape settle through real work, then copy the common
shape into a template repo and add it to `ecosystem/templates.yml`.
