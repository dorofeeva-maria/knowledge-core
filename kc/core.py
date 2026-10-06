"""Locate the core and load its registry / device overlay / .env.

The core is a checkout of the engine (`kc/` + `ecosystem/`). Its state files are created by
`kc bootstrap`, never shipped by the engine (ADR 0009), and read only by the core.
"""
import os
from pathlib import Path


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
    for k in ("KC_DEVICE_ID", "KC_LANGUAGE", "KC_CORE"):  # real env wins
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        raise SystemExit("kc: PyYAML is required — install it (pip install pyyaml)")


def load_registry(core):
    yaml = _yaml()
    f = core / "ecosystem" / "registry.yml"
    if not f.exists():
        return {}
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return data.get("modules") or {}


def load_instance(core):
    f = core / "ecosystem" / "instance.yml"
    if not f.exists():
        return {}
    return _yaml().safe_load(f.read_text(encoding="utf-8")) or {}


def load_devices(core):
    f = core / "ecosystem" / "devices.local.yml"
    if not f.exists():
        return {}
    return _yaml().safe_load(f.read_text(encoding="utf-8")) or {}


def resolve(core):
    """(modules, device_id). Each module: name, path(Path|None), status, external,
    write_zones, private, remote, upstream."""
    reg = load_registry(core)
    env = load_env(core)
    did = env.get("KC_DEVICE_ID")
    paths = ((load_devices(core).get(did) or {}).get("paths") or {}) if did else {}
    out = []
    for name, m in reg.items():
        m = m or {}
        p = paths.get(name)
        out.append({
            "name": name,
            "path": Path(p).expanduser().resolve() if p else None,
            "status": m.get("status", "active"),
            "external": bool(m.get("external", False)),
            "write_zones": m.get("write_zones") or [],
            "private": bool(m.get("private", False)),
            "remote": m.get("remote"),
            "upstream": m.get("upstream") if "upstream" not in m or m.get("upstream")
                        else "detached",
            "language": m.get("language"),
            "media": m.get("media", "media/"),
            "check": m.get("check"),
        })
    return out, did
