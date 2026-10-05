"""kc bootstrap — set up this device for a center fork.

Idempotent and re-runnable. Installs the `kc` launcher on PATH, configures the device
(`.env` + device overlay), installs the chosen assistants, and sets up (or skips) each
registry module on this device. External modules default to *not* set up locally.
"""
import os
import platform
import subprocess
from pathlib import Path
from . import center as C
from . import wrappers


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


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_yaml(path):
    return (C._yaml().safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


def _dump_yaml(path, data):
    _write(path, C._yaml().safe_dump(data, sort_keys=False, allow_unicode=True))


def install_launcher(center):
    bindir = Path.home() / ".local" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = bindir / "kc.cmd"
        launcher.write_text(
            f'@echo off\r\nset "KC_CENTER={center}"\r\n'
            f'set "PYTHONPATH={center};%PYTHONPATH%"\r\npython -m kc %*\r\n',
            encoding="utf-8")
    else:
        launcher = bindir / "kc"
        launcher.write_text(
            f'#!/bin/sh\nexport KC_CENTER="{center}"\n'
            f'export PYTHONPATH="{center}:$PYTHONPATH"\nexec python3 -m kc "$@"\n',
            encoding="utf-8")
        launcher.chmod(0o755)
    on_path = str(bindir) in os.environ.get("PATH", "").split(os.pathsep)
    return launcher, on_path


def run(center, device_id=None, agents=None, language=None, yes=False):
    # 1. instance language -> ecosystem/instance.yml (committed, shared across devices)
    inst_path = center / "ecosystem" / "instance.yml"
    inst = _load_yaml(inst_path)
    if language:
        inst["language"] = language
    elif "language" not in inst:
        inst["language"] = _ask("Instance language (e.g. en, ru)", "en", yes) or "en"
    _dump_yaml(inst_path, inst)

    # 2. device id -> .env (gitignored, per-device)
    if not device_id:
        device_id = _ask("Device id for this machine", platform.node() or "device", yes)
    env_path = center / ".env"
    keep = [l for l in (env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else [])
            if l.strip() and not l.strip().startswith("KC_DEVICE_ID=")]
    _write(env_path, "\n".join([f"KC_DEVICE_ID={device_id}"] + keep) + "\n")

    # 3. kc launcher on PATH
    launcher, on_path = install_launcher(center)

    # 4. assistants
    if not agents:
        a = _ask("Assistants on this device (comma-separated)", "claude", yes)
        agents = [x.strip() for x in (a or "").split(",") if x.strip()]
    for ag in agents:
        wrappers.add_agent(center, ag)

    # 5. per-module setup on this device
    devices_path = center / "ecosystem" / "devices.local.yml"
    devices = _load_yaml(devices_path)
    paths = devices.setdefault(device_id, {}).setdefault("paths", {})
    for name, m in C.load_registry(center).items():
        m = m or {}
        if m.get("status") == "disconnected":
            continue
        ext = bool(m.get("external"))
        if not _ask_yn(f"Set up module '{name}'{' (external)' if ext else ''} on this device?",
                       default=not ext, yes=yes):
            paths.pop(name, None)
            continue
        p = _ask(f"  path for '{name}'", str(center.parent / "projects" / name), yes)
        paths[name] = p
        remote = m.get("remote")
        if remote and not Path(p).expanduser().exists():
            print(f"  cloning {remote} -> {p}")
            subprocess.run(["git", "clone", remote, str(Path(p).expanduser())])
            # fork-model branch/upstream wiring is done by `kc new-module`; existing forks
            # already carry main/working.
    _dump_yaml(devices_path, devices)

    print("\nbootstrap complete:")
    print(f"  center    {center}")
    print(f"  device    {device_id}")
    print(f"  language  {inst['language']}")
    print(f"  kc        {launcher}" + ("" if on_path else f"   (add {launcher.parent} to PATH)"))
    print(f"  agents    {', '.join(agents) or '(none)'}")
    print(f"  modules   {', '.join(paths) or '(none yet)'}")
