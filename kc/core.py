"""Locate the core and read/write its state: registry, instance settings, device overlay, .env.

The core is a fork of the engine (`kc/` + `ecosystem/`). Its state files are created by
`kc bootstrap`, never shipped by the engine (ADR 0009).
"""
import os
import re
from pathlib import Path

STATUSES = ("active", "frozen")


def is_core(d):
    """A core is a checkout of the engine: it has the `kc` package and an `ecosystem/` folder."""
    return (Path(d) / "kc" / "__main__.py").exists() and (Path(d) / "ecosystem").is_dir()


def find_core(start=None):
    env = os.environ.get("KC_CORE")
    if env and is_core(env):
        return Path(env).resolve()
    p = Path(start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if is_core(d):
            return d
    return None


def yaml():
    try:
        import yaml as _y
        return _y
    except ImportError:
        raise SystemExit("kc: PyYAML is required — install it (pip install pyyaml)")


def read_yaml(path):
    path = Path(path)
    return (yaml().safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml().safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8", newline="\n")


def load_env(core):
    env = {}
    f = core / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("KC_DEVICE_ID",):  # real env wins
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def registry_path(core):
    return core / "ecosystem" / "registry.yml"


def load_registry(core):
    return read_yaml(registry_path(core)).get("modules") or {}


def save_registry(core, modules):
    write_yaml(registry_path(core), {"modules": modules})


def load_instance(core):
    return read_yaml(core / "ecosystem" / "instance.yml")


def device_id(core):
    return load_env(core).get("KC_DEVICE_ID")


def devices_path(core):
    return core / "ecosystem" / "devices.local.yml"


def norm_path(p):
    """A path typed by the human, absolute. On Windows, Git Bash paths (`/c/Users/...`) are
    turned into `C:/Users/...` so Python and git agree on them."""
    p = str(p).strip()
    if os.name == "nt":
        m = re.match(r"^/([a-zA-Z])(/.*)?$", p)
        if m:
            p = f"{m.group(1).upper()}:{m.group(2) or '/'}"
    return Path(p).expanduser().resolve()


def set_path(core, name, dest):
    """Record where module `name` lives on this device (gitignored overlay)."""
    did = device_id(core)
    if not did:
        print("  (KC_DEVICE_ID unset — path not recorded; run kc bootstrap)")
        return
    data = read_yaml(devices_path(core))
    data.setdefault(did, {}).setdefault("paths", {})[name] = str(dest)
    write_yaml(devices_path(core), data)


def modules(core):
    """Registry entries merged with this device's paths. Each: name, path (Path|None), status,
    external, private, remote, check, description, reviewed."""
    reg = load_registry(core)
    did = device_id(core)
    paths = ((read_yaml(devices_path(core)).get(did) or {}).get("paths") or {}) if did else {}
    out = []
    for name, m in reg.items():
        m = m or {}
        p = paths.get(name)
        out.append({
            "name": name,
            "path": Path(p).expanduser().resolve() if p else None,
            "status": m.get("status") or "active",
            "external": m.get("external") is True,
            "private": m.get("private") is True,
            "remote": m.get("remote"),
            "check": m.get("check"),
            "description": m.get("description") or "",
            "reviewed": m.get("reviewed") or {},
        })
    return out
