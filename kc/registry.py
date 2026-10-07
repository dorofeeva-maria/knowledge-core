"""The registry — the map of modules: `kc registry`, `kc set`, `kc reviewed`.

The registry (`ecosystem/registry.yml`) is the only place module facts live; the agent routes
by its descriptions and runs a module's processes from it (ADR 0015).
"""
import datetime
import re
from pathlib import Path
from . import core as C
from . import git as G

SETTABLE = {"description", "remote", "status", "private", "check"}


def _frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    kv = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            kv[m.group(1)] = m.group(2).strip().strip("\"'")
    return kv


def processes(path):
    """A module's processes: its Claude Code skills, `.claude/skills/<name>/SKILL.md`.
    Returns [(name, description, relative path)]."""
    if not path or not Path(path).is_dir():
        return []
    out = []
    for f in sorted(Path(path).glob(".claude/skills/*/SKILL.md")):
        fm = _frontmatter(f.read_text(encoding="utf-8", errors="replace"))
        out.append((fm.get("name") or f.parent.name, fm.get("description") or "",
                    f.relative_to(path).as_posix()))
    return out


def count_notes(path):
    """Markdown files in a module, outside hidden folders — the size signal for reviews."""
    if not path or not Path(path).is_dir():
        return 0
    p = Path(path)
    return sum(1 for f in p.rglob("*.md")
               if not any(part.startswith(".") for part in f.relative_to(p).parts))


def commit_registry(core, message):
    """Commit a registry change in the core right away, with a message saying what changed;
    the next sync pushes it."""
    G.git(core, "add", "ecosystem/registry.yml")
    G.git(core, "commit", "-q", "-m", message, "--", "ecosystem/registry.yml")


def show(core):
    mods = C.modules(core)
    print(f"core: {core}")
    print(f"device: {C.device_id(core) or '(KC_DEVICE_ID unset — run kc bootstrap)'}")
    if not mods:
        print("modules: none yet")
        return 0
    w = max(len(m["name"]) for m in mods)
    pad = " " * (w + 2)
    for m in mods:
        here = "here" if (m["path"] and m["path"].exists()) else "absent"
        flags = [m["status"]] + (["external"] if m["external"] else []) + (["private"] if m["private"] else [])
        print(f"  {m['name'].ljust(w)}  {here:6}  {' '.join(flags)}")
        if m["path"] and m["path"].exists():
            print(f"{pad}  path: {m['path']}")
        if m["description"]:
            print(f"{pad}  {m['description']}")
        for name, desc, rel in processes(m["path"]):
            print(f"{pad}  process {name}: {desc}  ({rel})")
    return 0


def _parse(k, v):
    if v.lower() in ("~", "none", "null", ""):
        return None
    if k == "private":
        if v.lower() in ("true", "yes", "1"):
            return True
        if v.lower() in ("false", "no", "0"):
            return False
        raise SystemExit("kc set: private must be true or false")
    if k == "status" and v not in C.STATUSES:
        raise SystemExit(f"kc set: status must be one of {', '.join(C.STATUSES)}")
    return v


def set_fields(core, name, pairs):
    """`kc set NAME key=value ...`. A new `remote` also becomes the module's origin and is
    pushed; a private module's remote must be private (checked here, once)."""
    reg = C.load_registry(core)
    if name not in reg:
        raise SystemExit(f"kc set: no module '{name}' in registry")
    entry = dict(reg[name] or {})
    changes = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"kc set: expected key=value, got '{pair}'")
        k, v = pair.split("=", 1)
        if k not in SETTABLE:
            raise SystemExit(f"kc set: '{k}' cannot be set (settable: {', '.join(sorted(SETTABLE))})")
        changes[k] = _parse(k, v)
    new = {**entry, **changes}
    if new.get("private") and ("remote" in changes or "private" in changes) and new.get("remote"):
        problem = G.private_problem(new["remote"])
        if problem:
            raise SystemExit(f"kc set: not changed — module '{name}' is private but {problem}")
    reg[name] = {k: v for k, v in new.items() if v is not None or k in ("remote",)}
    C.save_registry(core, reg)
    summary = ", ".join(f"{k}={v}" for k, v in changes.items())
    commit_registry(core, f"registry: set {name}: {summary}")
    print(f"set {name}: {summary}")
    if "remote" in changes:
        path = next((m["path"] for m in C.modules(core) if m["name"] == name), None)
        if path and G.is_repo(path) and not entry.get("external"):
            if changes["remote"]:
                G.git(path, "remote", "set-url" if G.has_origin(path) else "add", "origin", changes["remote"])
                print(f"  origin -> {changes['remote']}; pushed on the next `kc sync`")
            elif G.has_origin(path):
                G.git(path, "remote", "remove", "origin")
                print("  origin removed: the module stays on this device")
    return 0


def mark_reviewed(core, name):
    """`kc reviewed NAME` — record that the module's structure was just reviewed, so the start
    signal counts growth from here (ADR 0015)."""
    reg = C.load_registry(core)
    if name not in reg:
        raise SystemExit(f"kc reviewed: no module '{name}' in registry")
    path = next((m["path"] for m in C.modules(core) if m["name"] == name), None)
    reg[name] = {**(reg[name] or {}), "reviewed": {"date": datetime.date.today().isoformat(),
                                                   "notes": count_notes(path)}}
    C.save_registry(core, reg)
    commit_registry(core, f"registry: {name} structure reviewed")
    print(f"reviewed {name}: {reg[name]['reviewed']['notes']} notes as of {reg[name]['reviewed']['date']}")
    return 0
