# ecosystem/

The core's state: what the orchestrator knows about the ecosystem and the human — never subject
knowledge. The engine ships only this README; `kc bootstrap` creates the files below in your
core (ADR 0009).

| File | What | Who writes it |
|---|---|---|
| `registry.yml` | the map of modules (below) | `kc new-module`, `kc add-module`, `kc set`, `kc reviewed` |
| `memory.md` | standing facts about the human and corrections to the assistant | the agent, when the human states or corrects something lasting |
| `todo.md` | deferred work: `## Tasks`, `## Candidates` (new module, split, process), `## Repeats` (manual procedures and how often they were done) | the agent |
| `decisions.md` | decisions about the ecosystem (module created, split, frozen; a candidate rejected), newest first | the agent, when the human decides |
| `instance.yml` | settings shared by your devices: `language`, `review_after_notes`, `review_after_days` | `kc bootstrap`, by hand |
| `templates.yml` | optional: your own module templates, same format as `config/templates.yml` | by hand |
| `devices.local.yml` | gitignored: where each module lives on each device | `kc bootstrap`, `kc new-module`, `kc add-module` |

History is git. Decisions about the **engine** are ADRs in `docs/adr/`, not here.

## `registry.yml`

```yaml
modules:
  <name>:                       # kebab-case; the module's identity
    description: <text>         # one line: what it holds and what goes there — the agent routes by it
    remote: <git-url>           # where devices clone it from and push to; ~ = this device only
    status: active              # active | frozen
    private: false              # true = personal content: its remote must be private, details never surface elsewhere
    external: true              # only for repos that are not yours; absent = yours
    check: <command>            # optional: the module's read-only format check, run in its root
    reviewed: {date: YYYY-MM-DD, notes: N}   # last structure review (kc reviewed); absent date = never
```

What each value makes the core do:

- **`status: active`** — read, write, commit, sync.
- **`status: frozen`** — yours, but the subject is closed: read and pull only; no writes, no
  commits, no maintenance signals. Set it back to `active` to work on it again.
- **`external: true`** — not yours (e.g. a work repo): read only. kc fast-forwards it on its
  current branch when clean, never commits, pushes or checks it. It cannot become `active`.
- **`private: true`** — the remote must be a private repo: checked once, when the module gets
  its remote (`new-module`, `add-module`, `set remote=`) and at `bootstrap` (ADR 0015).
- **`check`** — run at every session start; a non-zero exit becomes a `format:` signal.
- **`reviewed`** — the start signal `structure:` fires when the module grew by
  `review_after_notes` notes, or grew at all and `review_after_days` passed since this date.

A module's processes are not listed here: they are the module's own Claude Code skills
(`.claude/skills/<name>/SKILL.md`), which `kc registry` reads from the module itself.

## `devices.local.yml`

```yaml
<device-id>:            # KC_DEVICE_ID from .env
  paths:
    <module>: /absolute/path/on/this/device
```

A module missing from `paths` is not on this device; kc skips it.
