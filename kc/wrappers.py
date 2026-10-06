"""Generate per-AI command wrappers + startup stubs from the canon (skills/ + AGENTS.md).

An adapter (`adapters/<agent>/adapter.yml`) declares, for one assistant, where its thin
wrappers go, its canon pointer, and how to install its session-start stub. Wrappers are
regenerated from the canon on each session start, so they never drift. They are
instance/device artifacts — gitignored, not committed.
"""
import json
from pathlib import Path
from . import core as C
from . import maintain


def _adapter(core, agent):
    f = core / "adapters" / agent / "adapter.yml"
    if not f.exists():
        raise SystemExit(
            f"kc: no adapter for '{agent}' (expected adapters/{agent}/adapter.yml). "
            f"Any assistant can still read AGENTS.md directly."
        )
    return C._yaml().safe_load(f.read_text(encoding="utf-8")) or {}


def _skills(core):
    d = core / "skills"
    out = []
    if d.exists():
        for p in sorted(d.glob("*.md")):
            if p.name == "README.md":
                continue
            fm = maintain.frontmatter(p.read_text(encoding="utf-8")) or {}
            out.append((p.stem, fm.get("description", p.stem)))
    return out


def _merge_json(path, fragment):
    cur = {}
    if path.exists():
        try:
            cur = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cur = {}

    def merge(a, b):
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(a.get(k), dict):
                merge(a[k], v)
            elif isinstance(v, list):
                # entries owned by kc (a command starting with "kc ") are replaced, not kept
                lst = [x for x in a.get(k, []) if '"command": "kc ' not in json.dumps(x)]
                a[k] = lst
                for item in v:
                    if item not in lst:          # idempotent for identical entries
                        lst.append(item)
            else:
                a[k] = v
        return a

    merge(cur, fragment)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_wrappers(core, agent):
    a = _adapter(core, agent)
    written = []
    w = a.get("wrapper")
    if w:
        skills = _skills(core)
        for skill, desc in skills:
            path = core / w["path"].format(skill=skill)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(w["body"].format(skill=skill, description=desc), encoding="utf-8")
            written.append(path.relative_to(core).as_posix())
        # remove wrappers of skills that no longer exist (generated files only: same template)
        keep = {(core / w["path"].format(skill=s)).resolve() for s, _ in skills}
        marker = w["body"].split("{skill}")[-1].strip().splitlines()[-1].strip()
        for old in (core / w["path"].format(skill="x")).parent.glob("*" + Path(w["path"]).suffix):
            if old.resolve() not in keep and marker and marker in old.read_text(encoding="utf-8", errors="replace"):
                old.unlink()
                print(f"ensure-wrappers [{agent}]: removed stale {old.relative_to(core).as_posix()}")
    p = a.get("pointer")
    if p:
        (core / p["path"]).write_text(p["body"], encoding="utf-8")
        written.append(p["path"])
    s = a.get("startup")
    if s and s.get("merge_json"):
        _merge_json(core / s["file"], s["merge_json"])
        written.append(s["file"])
    print(f"ensure-wrappers [{agent}]: {len(written)} file(s)"
          + (f" — {', '.join(written)}" if written else " (no skills yet)"))
    return written


def add_agent(core, agent):
    _adapter(core, agent)  # validates adapter exists
    ensure_wrappers(core, agent)
    print(f"add-agent: '{agent}' installed")
