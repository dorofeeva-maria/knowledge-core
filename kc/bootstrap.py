"""kc bootstrap — set up this device for a core. Idempotent and re-runnable.

1. Instance settings and the core's state files (created here, never shipped — ADR 0009).
2. This device's id (`.env`) and module paths (`ecosystem/devices.local.yml`), cloning modules
   that have a remote.
3. The privacy check: the core and every private module must have a private remote (ADR 0015).
4. Claude Code hooks for this device (`.claude/settings.local.json`): sync at session start and end.
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from . import core as C
from . import git as G

STATE = {
    "registry.yml": "modules: {}\n",
    "memory.md": """# Memory

Standing facts about the human and corrections to the assistant — read at every session start.
One bullet each: the fact, then **Why:** in a few words. Update or remove a fact that turns out
wrong. Rules that belong to one module go to that module's `AGENTS.md`, not here.
""",
    "todo.md": """# Todo

Deferred work. One line per item; delete the line when it is done or rejected.

## Tasks

## Candidates

## Repeats

<!-- A manual procedure done more than once: `- 2× · what was done · module · last YYYY-MM-DD`.
     Bump the count each time; at 3× kc raises it at session start. -->
""",
    "decisions.md": """# Decisions

Decisions about this ecosystem (module created, split, frozen; a candidate rejected), newest
first:

    ## YYYY-MM-DD — short title
    - **Options:** what was on the table
    - **Chosen:** what we do, and why
""",
}


try:                                     # typed paths may be Cyrillic: read stdin as UTF-8
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def clone(remote, dest):
    """Clone a module; on failure remove what the clone left behind. Returns True on success."""
    dest = Path(dest)
    existed = dest.exists()
    r = subprocess.run(["git", *G.LONGPATHS, "clone", "--quiet", remote, str(dest)])
    if r.returncode != 0 and not existed and dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    if r.returncode == 0 and G.LONGPATHS:
        G.git(dest, "config", "core.longpaths", "true")
    return r.returncode == 0


def attach(core, name, path=None):
    """`kc attach NAME [--path P]` — set up on this device a module registered elsewhere."""
    m = C.load_registry(core).get(name)
    if m is None:
        raise SystemExit(f"kc attach: no module '{name}' in the registry")
    did = C.device_id(core)
    if not did:
        raise SystemExit("kc attach: this device is not set up — run kc bootstrap first")
    dest = C.norm_path(path) if path else C.default_module_path(core, name)
    remote = (m or {}).get("remote")
    if not dest.exists():
        if not remote:
            raise SystemExit(f"kc attach: '{name}' has no remote and is not at {dest}")
        print(f"cloning {remote} -> {dest}")
        if not clone(remote, dest):
            raise SystemExit(f"kc attach: clone failed — nothing changed")
    elif not G.is_repo(dest):
        raise SystemExit(f"kc attach: {dest} exists but is not a git repo")
    if (m or {}).get("private") and remote:
        G.enforce_private(remote, "kc attach")
    C.set_path(core, name, dest)
    C.grant_module_dirs(core)
    print(f"attached '{name}' on this device: {dest}")
    return 0


def _ask(prompt, default=None, yes=False):
    if yes:
        return default
    try:
        v = input(prompt + (f" [{default}]" if default else "") + ": ").strip()
    except EOFError:
        v = ""
    return v or default


def _ask_yn(prompt, default=True, yes=False):
    if yes:
        return default
    v = _ask(f"{prompt} ({'Y/n' if default else 'y/N'})", "", yes=False)
    return default if not v else v.lower().startswith("y")


def ensure_state(core):
    created = []
    for rel, text in STATE.items():
        f = core / "ecosystem" / rel
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8", newline="\n")
            created.append(f"ecosystem/{rel}")
    return created


def install_hooks(core):
    """Write this device's hooks into `.claude/settings.local.json` (gitignored), with the
    absolute path of this Python, so hooks work the same in any shell. Other keys are kept."""
    data = C.read_local_settings(core)
    py = Path(sys.executable).as_posix()
    run = lambda ev: f'cd "$CLAUDE_PROJECT_DIR" && "{py}" -m kc hook {ev}'
    hooks = data.setdefault("hooks", {})
    hooks["SessionStart"] = [{"matcher": "startup|resume|clear",
                              "hooks": [{"type": "command", "command": run("start"), "timeout": 120}]}]
    hooks["SessionEnd"] = [{"hooks": [{"type": "command", "command": run("end"), "timeout": 60}]}]
    return C.write_local_settings(core, data)


def _gh_status():
    r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True) if shutil.which("gh") else None
    return "missing" if r is None else ("ok" if r.returncode == 0 else "not logged in")


def run(core, device_id=None, language=None, yes=False):
    # 1. instance + state
    inst_path = core / "ecosystem" / "instance.yml"
    inst = C.read_yaml(inst_path)
    if language:
        inst["language"] = language
    if "language" not in inst:
        inst["language"] = _ask("Language to write in (e.g. en, ru)", "en", yes) or "en"
    inst.setdefault("review_after_notes", 25)
    inst.setdefault("review_after_days", 60)
    C.write_yaml(inst_path, inst)
    created = ensure_state(core)
    G.git(core, "add", "ecosystem/instance.yml", *created)
    G.git(core, "commit", "-q", "-m", "core: instance settings and state files",
          "--", "ecosystem/instance.yml", *created)

    # 2. privacy: the core always holds private content
    url = G.origin_url(core)
    level, problem = G.private_problem(url) if url else (None, None)
    warnings = []
    if level == "warn":      # not verifiable: the human makes sure it is private
        warnings.append(f"the core's origin: {problem}")
    elif level == "stop":
        raise SystemExit(f"kc bootstrap: STOP — the core's origin: {problem}.\n"
                         f"  The core holds personal content and is pushed automatically. Point it at "
                         f"a private repo:\n  git remote set-url origin <private-url>   (then re-run)")

    # 3. device
    if not device_id:
        device_id = _ask("Device id for this machine", C.device_id(core) or platform.node() or "device", yes)
    env_path = core / ".env"
    keep = [l for l in (env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else [])
            if l.strip() and not l.strip().startswith("KC_DEVICE_ID=")]
    env_path.write_text("\n".join([f"KC_DEVICE_ID={device_id}"] + keep) + "\n", encoding="utf-8", newline="\n")

    # 4. modules on this device (check the settings file first, so a failure changes nothing)
    C.read_local_settings(core)
    devices = C.read_yaml(C.devices_path(core))
    paths = devices.setdefault(device_id, {}).setdefault("paths", {})
    for name, m in C.load_registry(core).items():
        m = m or {}
        ext = m.get("external") is True
        here = name in paths            # already set up on this device: keep it by default
        if not _ask_yn(f"Set up module '{name}'{' (external)' if ext else ''} on this device?",
                       default=here or not ext, yes=yes):
            if here and not _ask_yn(f"  '{name}' is set up here ({paths[name]}). Remove it from this "
                                    f"device's list? Files stay.", default=False, yes=yes):
                continue
            paths.pop(name, None)
            continue
        default = paths.get(name) or str(core.parent / "projects" / name)
        dest = C.norm_path(_ask(f"  path for '{name}'", default, yes))
        remote = m.get("remote")
        if not dest.exists():
            if not remote:
                print(f"  '{name}' has no remote and is not here — skipped")
                paths.pop(name, None)
                continue
            print(f"  cloning {remote} -> {dest}")
            if not clone(remote, dest):
                print(f"  clone failed — skipped '{name}'")
                continue
        if m.get("private") and remote:
            _, p = G.private_problem(remote)
            if p:
                warnings.append(f"module '{name}' is private but {p}")
        paths[name] = str(dest)
    C.write_yaml(C.devices_path(core), devices)

    # 5. hooks + access to module folders
    hooks = install_hooks(core)
    C.grant_module_dirs(core)

    print("\nbootstrap complete:")
    print(f"  core      {core}")
    print(f"  device    {device_id}")
    print(f"  language  {inst['language']}")
    print(f"  modules   {', '.join(paths) or '(none yet)'}")
    print(f"  hooks     {hooks.relative_to(core).as_posix()} (sync at session start and end)")
    print(f"  gh        {_gh_status()}")
    for w in warnings:
        print(f"  WARNING   {w}")
    return 1 if warnings else 0
