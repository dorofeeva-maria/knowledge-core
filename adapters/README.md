# adapters/

One folder per known AI assistant. An adapter knows how to render, for its assistant,
from the canon (`AGENTS.md` + `skills/`):

- **wrappers** — the assistant's native "slash commands" that point at a skill;
- **a startup stub** — the assistant's session-start hook/config that calls
  `kc ensure-wrappers --agent <self>`, so wrappers auto-regenerate from the canon on
  each start (mechanical, no approval).

`bootstrap` asks which assistant(s) you use on this device and installs their stubs +
generates their wrappers. `kc add-agent <name>` adds one later.

If an assistant has **no** adapter, it still works: every assistant can read `AGENTS.md`
directly (the universal fallback). Adding a new adapter is a contribution back to the engine.

- `claude/` — first adapter (Claude Code: `.claude/commands/*` + `CLAUDE.md` pointer + SessionStart hook).
