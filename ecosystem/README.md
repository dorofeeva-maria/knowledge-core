# ecosystem/

Core state — the orchestrator's **meta-knowledge about the ecosystem** (never domain
knowledge). Read **only by the core**; modules never read these files. The engine ships
them empty; a core fork fills them on its `main` branch.

- `registry.yml` — canonical module facts (below).
- `HOME.md` — one-screen map of every module (purpose, entry points): the front door.
- `todo/` — pending work, one file per item (leftover inbox/drafts, candidates, adaptations,
  deferred tasks); walked through at session start. See `todo/README.md`.
- `decisions.md` — decisions about the ecosystem (module created/split/frozen/detached,
  pending item rejected), newest first.
- `instance.yml` — instance settings shared by your devices: default `language`, the engine
  URL (`upstream`).
- History is git: the core's commits; automatic actions by `kc` are commits prefixed `auto:`
  (`git log --grep '^auto:'`).
- `templates.yml` — catalog of module templates offered when creating a module (name →
  source + "when" hint). Engine ships defaults; add your own. A module's chosen template is
  recorded in its registry entry (`upstream`).

Per-device absolute paths are **not** here; they live in the gitignored device overlay
`devices.local.yml`, created by `bootstrap`.

## How to write `registry.yml`

Map of `modules:`, keyed by module name. Each entry has exactly these fields — add nothing
"just in case"; every field exists because the core reads it to decide behavior.

```yaml
modules:
  <name>:                 # key = module identity, used in HOME, todo and decisions
    remote: <git-url>     # where to clone it on a new device and where to push; ~ = local-only, not pushed yet
    upstream: <git-url>   # the template it follows; ~ = none (bare or detached)
    external: false       # true = not ours / limited access (e.g. a work repo); gates writes
    write_zones: []       # only when external: paths the core may write to; [] = read-only
    status: active        # active | frozen | disconnected
    private: false        # true = never surface its details in unrelated/public places
    language: ru          # optional: language to write in; absent = session language
    media: media/         # optional: where source media goes; absent = media/; false = not kept
    check: <command>      # optional: the module's own read-only format check, run in its root
```

Field semantics (what each value makes the core do):

- **`remote`** — a URL lets `bootstrap` clone the module and `close` push it. `~` (empty)
  means the module exists only locally for now; the core skips pushing it.
- **`upstream`** — the format-template the module follows. Every device restores it as the
  module's `upstream` remote; `kc pull-all` rebases the module onto template updates. `~` = no
  template: created bare, or detached with `kc detach NAME` (the remote is then removed on
  every device). A missing key means "unknown" — the core leaves the remote alone.
- **`external`** — `true` tells the core this repo is not ours: never write to it except
  within `write_zones`. `false` = ours, full write (subject to `status`).
- **`write_zones`** — meaningful only with `external: true`. Lists the sub-paths the core
  may write into; empty list = treat the external module as read-only.
- **`status`**
  - `active` — full participation: read, write, pull.
  - `frozen` — read and pull, **no writes** (retired-but-kept, e.g. an archived project).
    "Offloaded to GitHub, read on demand" = `frozen` **and** no path in the device overlay.
  - `disconnected` — the core ignores it entirely (no read/write/pull). The entry stays
    so we remember it was intentionally retired, not accidentally lost.
- **`private`** — `true` makes the core keep the module's specifics out of unrelated
  cross-references and out of anything that could become public.
- **`language`** — optional. The language the core writes into this module. Absent: the
  session language (`KC_LANGUAGE`, else `instance.yml` `language`).
- **`media`** — optional. Folder (inside the module) where processed source media goes —
  PDFs, images, audio, video — with transcripts beside them; files over the size limit go to
  `<media>/large/`, which the module's `.gitignore` excludes. Absent: `media/`. `false`: the
  module keeps no media (only the distilled notes).

- **`check`** — optional. A read-only command, run in the module's root, that checks the
  module's format (for template modules it comes from the template catalog). Run by
  `kc pull-all` and in `close`; a non-zero exit is reported as format issues (ADR 0008).
- **`status: frozen`** with no path on this device — read it on demand from `remote` (web/API).

Settings are optional, so any repo can be a module as is (ADR 0007). When a module is created
or promoted, the agent also writes the same conventions in plain words into the module's own
`AGENTS.md` ("Write in Russian. Keep source files in media/."), so an assistant working in the
module alone follows them too. If the two disagree, the agent proposes to sync them.

Not stored here, on purpose: per-device presence (device overlay path present or absent).

## How to write the device overlay `devices.local.yml` (gitignored)

Keyed by device id (matching `KC_DEVICE_ID` in `.env`). Only paths — a module absent from
`paths` simply is not on this device.

```yaml
<device-id>:
  paths:
    <module>: /absolute/path/on/this/device
```
