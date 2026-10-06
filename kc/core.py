"""Locate the center and load its registry / device overlay / .env.

The center is the repo that holds `ecosystem/registry.yml`. These files are read
ONLY here (by the center); modules never read them.
"""
import os
from pathlib import Path


def find_center(start=None):
    env = os.environ.get("KC_CENTER")
    if env and (Path(env) / "ecosystem" / "registry.yml").exists():
        return Path(env).resolve()
    p = Path(start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / "ecosystem" / "registry.yml").exists():
            return d
    return None


def load_env(center):
    env = {}
    f = center / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("KC_DEVICE_ID", "KC_LANGUAGE", "KC_CENTER"):  # real env wins
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        raise SystemExit("kc: PyYAML is required — install it (pip install pyyaml)")


def load_registry(center):
    yaml = _yaml()
    data = yaml.safe_load((center / "ecosystem" / "registry.yml").read_text(encoding="utf-8")) or {}
    return data.get("modules") or {}


def load_devices(center):
    f = center / "ecosystem" / "devices.local.yml"
    if not f.exists():
        return {}
    return _yaml().safe_load(f.read_text(encoding="utf-8")) or {}


def resolve(center):
    """(modules, device_id). Each module: name, path(Path|None), status, external,
    write_zones, private, remote."""
    reg = load_registry(center)
    env = load_env(center)
    did = env.get("KC_DEVICE_ID")
    paths = ((load_devices(center).get(did) or {}).get("paths") or {}) if did else {}
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
        })
    return out, did
