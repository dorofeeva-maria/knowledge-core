# todo/

Pending work of the ecosystem — one file per item, committed, so every device sees it.
At session start `kc todo` lists it and the agent walks through it with the human
(`skills/todo.md`): **apply**, **defer**, or **reject** each item, or defer everything at once.

Item format (`YYYY-MM-DD-<kind>-<slug>.md`):

```markdown
---
title: What to do, in one line
type: todo
kind: inbox | draft | candidate | adaptation | task
source: inbox/file.pdf          # raw file, commit range, or module path the item is about
target: <module> | core         # where the result goes, if known
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

What to do, decisions already taken, what deferring it affects.
```

- `inbox` / `draft` — a raw file left unprocessed (stubs are created by `kc todo`).
- `candidate` — a theme, script or process proposed for its own module or tool-package.
- `adaptation` — content to adapt to a template/engine update (`skills/update.md`).
- `task` — any deferred large task (AGENTS.md, *Large tasks*).

Applied → delete the item (and its processed source). Rejected → delete the item and its
source (media excepted) and add an entry to `../decisions.md`.
