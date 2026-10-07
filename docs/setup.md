# Setup

## Prerequisites

- **git**, **Python 3.9+** and **PyYAML** (`pip install pyyaml`). Commands below say `python3`;
  on Windows use `python` (there `python3` is often a Microsoft Store stub).
- **Claude Code.**
- **GitHub CLI** (`gh`), logged in (`gh auth login`): `kc` uses it to verify that private repos
  really are private, and it is the easiest way to create them.

## Start your ecosystem (first device)

1. Copy the engine into a new **private** repo — your core:

   ```sh
   git clone https://github.com/dorofeeva-maria/knowledge-core my-core
   cd my-core
   git remote remove origin
   gh repo create my-core --private --source . --push
   ```

   The core has no link to the engine afterwards: it is yours to change.
2. Set up this device: `python3 -m kc bootstrap` — language, device id. It creates the state
   files in `ecosystem/`, checks that the core's origin is private, and installs the session
   hooks in `.claude/settings.local.json` (this device only).
3. Start Claude Code in the core: `claude`. The start hook syncs and reports.
4. Create modules as you need them (the agent proposes; you create the remote):

   ```sh
   gh repo create my-notes --private
   python3 -m kc new-module notes --template info --private \
       --remote https://github.com/<you>/my-notes.git --description "What goes here"
   ```

   Without `--path` a module goes next to the modules already on this device (the first one:
   `<core>/../projects/NAME`). Register a repo you already have:
   `python3 -m kc add-module NAME PATH` (`--external` for a repo that is not yours — read only).
   A module created from a template URL not in the catalog gets its format check with
   `--check "python tools/notes.py check"`.

## Add another device

```sh
git clone <your-core-url> my-core && cd my-core
python3 -m kc bootstrap
```

For each module, choose whether it lives on this device and where; modules with a remote are
cloned. A module without a remote stays on the device where it was created. Re-running
`bootstrap` keeps the device id and the modules already set up here.

A module created later on another device shows up in the start report as "not set up on this
device"; set it up with `python3 -m kc attach NAME [--path P]`.

## Day to day

- Start Claude Code in the core. Talk; the agent writes into modules as you go.
- Sessions sync on start and end. Switching devices mid-session: ask the agent to sync, or run
  `python3 -m kc sync`.
- `python3 -m kc status` shows unpushed work and signals without touching the network.
