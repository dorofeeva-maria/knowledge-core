# adapters/

One folder per known AI assistant, each with an `adapter.yml` that tells
`kc ensure-wrappers --agent <name>` how to render the canon (`AGENTS.md` + `skills/`) for
that assistant:

- **wrapper** — a thin "slash command" per skill that points back at `skills/<name>.md`;
- **pointer** — the assistant's canon entry file (e.g. `CLAUDE.md`) pointing at `AGENTS.md`;
- **startup** — hooks that call `kc hook <event>`: on session start they regenerate wrappers
  from the canon, sync repos and list pending work; during and at the end of a session they
  keep the session draft (see below).

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
transcript:                   # optional: lets kc keep the session draft (ADR 0006)
  format: <reader>            # e.g. claude-jsonl
  include_tool_results: [..]  # tools whose results are the human's words
startup:                      # optional: hook integration
  file: "<path>"
  merge_json: { ... }         # deep-merged into a JSON file; list entries whose command
                              # starts with "kc " are replaced, never duplicated
```

Hooks call `kc hook <event> --agent <name>` with the assistant's event JSON on stdin:
`session-start` (sync, todo, wrappers, session bookkeeping), `stop` (count turns; capture the
draft in the background when due), `pre-compact` and `session-end` (capture now; at the end,
warn if the session was not closed). An assistant without transcript access still works; it
just has no automatic draft.

Placeholders: `{skill}` = skill file stem, `{description}` = skill frontmatter `description`.
`merge_json` suits JSON-config assistants (like Claude Code); assistants with other config
shapes get their own directive as the adapter set grows.

- `claude/` — Claude Code (`.claude/commands/*` wrappers, `CLAUDE.md` pointer, SessionStart / Stop / PreCompact / SessionEnd hooks, JSONL transcript).
