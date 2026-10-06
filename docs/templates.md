# Authoring a format-template

A **format-template** is a separate git repo that scaffolds a recurring *kind* of module. New
modules are forked from it (the fork sets the template as `upstream`; see the fork model in
`architecture.md`). The catalog of available templates is `ecosystem/templates.yml`.

## Rules

- **No ecosystem references.** A template's files *are* the new module's starting content —
  all inherited by the fork. So a template must read as a normal, standalone repo: no mention
  of the core, registry, `kc`, "ecosystem", the fork model, or its own template-ness. (This
  authoring doc is the only place that talks about templates — it lives in the engine, never
  inside a template.)
- **Ship placeholders, rewritten on first use.** A module `AGENTS.md` describing the module, a
  `README`, a folder skeleton, maybe a starter note — all clearly meant to be replaced.
- **Encode the type's structure** (folders, starter notes) so a new module of this kind starts
  shaped right. Keep it minimal; don't over-impose.
- **The template owns its format tools.** If the format has rules a machine can check (an
  index, frontmatter, links, log size), ship the tools in the template (e.g. `tools/`) and
  describe them in its `AGENTS.md`, so a module opened alone can keep itself in shape. Declare
  the read-only check command in the catalog (`ecosystem/templates.yml`, field `check`); the
  core copies it into the registry of each new module and runs it (ADR 0008). Other
  model-agnostic scripts or automations are welcome too. No ecosystem references.
- **Fork model:** a module keeps its content on `main`; the template is its `upstream` and
  template changes are rebased under the module's content. So publish changes that a module
  can absorb; describe any change that needs module content adapted in the commit message.

## Checklist (before publishing or extracting a template)

1. **No ecosystem references:** `kc check-template <template-dir>` reports clean (review any
   flagged lines — a module repo must not mention the core, registry, `kc`, the fork model,
   or its own template-ness).
2. **Standalone adequacy:** `AGENTS.md` alone lets an assistant build an adequate module
   *without the core* — it explains, in tool-neutral terms, how to add notes (frontmatter +
   TL;DR), the folder structure, how to link, and how to keep `index.md` and `log.md`. If an
   assistant with only this repo couldn't produce a sensible module, the template is not ready.

## Using a template (fork → first-use rewrite)

`kc new-module` forks the template and sets it as `upstream` (content stays on `main`). Then the
assistant **clarifies the new module's purpose and structure with the user** and
rewrites the placeholders into the module's real identity, removing any leftover template text.
The module repo must end up with zero ecosystem references. See the `emergence` skill.

## How a template is born

Do not invent process-type templates up front — a single generic one is usually pointless.
Let a module's shape stabilize through real work, then extract the common shape into a template
(`emergence` → "extract a format-template"). The engine ships only the `info` template as a
starting point; process templates emerge from use.
