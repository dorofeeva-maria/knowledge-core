# Setup

How anyone creates an ecosystem from this engine, and how to add it to another device.

## Prerequisites (any OS)

- **git** and **Python 3.9+**. Commands below say `python3`; on Windows use `python` (there
  `python3` is often a Microsoft Store stub). After bootstrap, the `kc` launcher picks the right
  one, and module checks that start with `python` run with the same interpreter as `kc`.
- **PyYAML**: `pip install pyyaml` (used by `kc`).
- **GitHub CLI `gh`** — install (`brew install gh`, `winget install GitHub.cli`, or see
  cli.github.com) and run `gh auth login`. `kc` uses it to verify that private content (the core,
  a `private` module) is pushed only to a private repo; without it, private/core pushes refuse
  (ADR 0014).
- A directory on your `PATH` for the launcher — `~/.local/bin` on macOS/Linux,
  `%USERPROFILE%\.local\bin` on Windows. `kc bootstrap` writes the launcher there and tells
  you if it isn't on `PATH` yet.

## Create a new ecosystem (fresh)

1. Clone the engine into your core folder:
   `git clone <engine-url> my-core`
2. Make the engine your upstream (fork model: content on `main`, engine updates rebased under it):
   `cd my-core && git remote rename origin upstream && git branch --unset-upstream`
3. (Optional, for multi-device / backup) create your own empty repo and add it:
   `git remote add origin <your-core-url>`
4. Bootstrap this device (records the engine URL, installs `kc` on `PATH`, generates your
   assistant's wrappers, records the device):
   `python3 -m kc bootstrap`  → answer: language, device id, assistant(s). It creates the core's
   state files (`ecosystem/registry.yml`, `decisions.md`, `todo/`, `instance.yml`).
5. Log in to GitHub: `gh auth login` — required before the first push, since `kc` verifies your
   core's `origin` is a private repo before pushing private content (ADR 0014).
6. Push your core (if you added an origin): `kc push-all`.
7. Create modules as you need them:
   `kc new-module NAME --template info`  (or `--no-template`, or `--template-url <url>`),
   or register repos you already have: `kc add-module NAME PATH` (`--external` if not yours).

You now have a working, empty ecosystem. Everything is yours; nothing references the engine
except the `upstream` remote.

## Add the ecosystem to another device

1. Clone your core:
   `git clone <your-core-url> my-core && cd my-core`
2. Log in to GitHub on this device: `gh auth login` (same reason as above — needed for pushes).
3. Bootstrap with a new device id:
   `python3 -m kc bootstrap`  → for each module, choose whether to set it up here; modules with
   a remote are cloned to this device's path. **Local-only modules (no remote) can't travel** —
   push them to a remote first if you want them on more than one device.
4. From now on, each session start pulls the core and present modules.

Notes:
- Every device restores the `upstream` remotes (engine from `ecosystem/instance.yml`, templates
  from the registry) and may apply updates; the sync order makes this safe (ADR 0003).
- Per-device absolute paths live in the gitignored `ecosystem/devices.local.yml`; the committed
  registry stays device-agnostic.
- Protect the public engine and template repos on the host: allow changes to `main` only via pull
  request, so a misconfigured push can never land private core content there (ADR 0014).

## OS notes

- **Launcher:** `~/.local/bin/kc` (shell) on macOS/Linux; `…\.local\bin\kc.cmd` on Windows.
  Ensure that directory is on `PATH`.
- Paths, branch logic, and the launcher are handled per-OS by `kc bootstrap`.
