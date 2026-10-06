# adapters/

One folder per known AI assistant, each with an `adapter.yml` that tells
`kc ensure-wrappers --agent <name>` how to render the canon (`AGENTS.md` + `skills/`) for
that assistant:

- **wrapper** — a thin "slash command" per skill that points back at `skills/<name>.md`;
- **pointer** — the assistant's canon entry file (e.g. `CLAUDE.md`) pointing at `AGENTS.md`;
- **startup** — the session-start stub that re-runs `kc ensure-wrappers` (+ `pull-all`,
  `todo`) so wrappers regenerate from the canon on every start and never drift.

`bootstrap` asks which assistant(s) you use on this device and installs their stubs;
`kc add-agent <name>` adds one later. Generated wrappers are **gitignored** — they are
instance/device artifacts, not committed.

If an assistant has **no** adapter it still works: every assistant can read `AGENTS.md`
directly (the universal fallback). Adding an adapter is a contribution back to the engine.

## `adapter.yml` format

```yaml
name: <agent>
wrapper:                      # optional: one file per skill
  path: "<path with {skill}>"
  body: "<template with {skill} and {description}>"
pointer:                      # optional: a single canon-entry file
  path: "<path>"
  body: "<text>"
startup:                      # optional: session-start integration
  file: "<path>"
  merge_json: { ... }         # deep-merged into a JSON file (idempotent)
```

Placeholders: `{skill}` = skill file stem, `{description}` = skill frontmatter `description`.
`merge_json` suits JSON-config assistants (like Claude Code); assistants with other config
shapes get their own directive as the adapter set grows.

- `claude/` — Claude Code (`.claude/commands/*` wrappers, `CLAUDE.md` pointer, SessionStart hook).
