# skills/

AI-agnostic markdown instructions for **cognitive** operations — the ones that need
judgment (reading a session, deciding where knowledge goes, asking the human,
proposing structure). Each skill is the single source of truth; `adapters/` render
thin per-AI wrappers (e.g. a Claude slash command) that just point here.

Planned skills (content added incrementally, with sign-off):

- `close.md` — consolidate a session: route its draft into modules, reconcile, run `kc`, commit/push.
- `inbox.md` — process raw/dropped material into the right module.
- `emergence.md` — propose a new module, a tool-package extraction, or a module split.

A skill tells the assistant **when to call the mechanical `kc` CLI**; it never
reimplements mechanical work.
