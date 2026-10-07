"""Create and register modules: `kc templates`, `kc new-module`, `kc add-module`.

A template is a starting copy: its files are copied into a fresh repo with its own history, and
the module never hears from the template again (ADR 0015).
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from . import core as C
from . import git as G
from .registry import count_notes, commit_registry


def list_templates(core):
    """Engine defaults (config/templates.yml) overlaid by the core's own (ecosystem/templates.yml)."""
    out = {}
    for f in (core / "config" / "templates.yml", core / "ecosystem" / "templates.yml"):
        out.update(C.read_yaml(f).get("templates") or {})
    return out


def show_templates(core):
    t = list_templates(core)
    if not t:
        print("templates: none in catalog")
        return 0
    w = max(len(k) for k in t)
    for name, m in t.items():
        m = m or {}
        print(f"  {name.ljust(w)}  {m.get('source', '?')}")
        if m.get("when"):
            print(f"  {' ' * w}  {m['when']}")
    return 0


def describe(path):
    """Default description: the first prose line of the module's README / AGENTS.md."""
    for fn in ("README.md", "AGENTS.md"):
        f = Path(path) / fn
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s and not s.startswith(("#", ">", "|", "```", "<", "---", "-", "*")):
                return s[:200]
    return ""


BARE_AGENTS = """# {name}

What this module holds and what goes here — one line, then the rules for working in it.

## How to work here

- Write notes as markdown with frontmatter (`title`, `type`, `updated: YYYY-MM-DD`).
- Link other notes in this repo with relative markdown links: `[text](path/to/note.md)`.
- Processes of this module (repeatable procedures) live in `.claude/skills/<name>/SKILL.md`.
"""


def _copy_template(source, dest):
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["git", "clone", "--quiet", "--depth", "1", source, tmp],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise SystemExit(f"kc new-module: cannot fetch template {source}: {G.last(r.stderr)}")
        shutil.copytree(tmp, dest, ignore=shutil.ignore_patterns(".git"))


def new_module(core, name, template=None, template_url=None, no_template=False, path=None,
               remote=None, private=False, description=None):
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or name == "core":
        raise SystemExit("kc new-module: NAME must be kebab-case and not 'core'")
    if name in C.load_registry(core):
        raise SystemExit(f"kc new-module: '{name}' is already registered")
    dest = C.norm_path(path) if path else (core.parent / "projects" / name).resolve()
    if dest.exists():
        raise SystemExit(f"kc new-module: {dest} already exists")
    if private and remote:
        problem = G.private_problem(remote)
        if problem:
            raise SystemExit(f"kc new-module: the module is private but {problem}")

    check, source = None, None
    if not no_template:
        source = template_url
        if not source and template:
            t = list_templates(core).get(template)
            if not t:
                raise SystemExit(f"kc new-module: no template '{template}' (see `kc templates`)")
            source, check = t.get("source"), t.get("check")
        if not source:
            raise SystemExit("kc new-module: choose --template NAME, --template-url URL, or --no-template")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if source:
        _copy_template(source, dest)
    else:
        dest.mkdir(parents=True)
        (dest / "AGENTS.md").write_text(BARE_AGENTS.format(name=name), encoding="utf-8", newline="\n")
        (dest / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8", newline="\n")
    G.git(dest, "init", "-q", "-b", G.BRANCH)
    G.commit_all(dest, f"Start {name}" + (f" from template {template or source}" if source else ""))
    if remote:
        G.git(dest, "remote", "add", "origin", remote)
        status, _ = G.sync_own(dest, f"Start {name}")
        print(f"  origin -> {remote}: {status}")

    reg = C.load_registry(core)
    reg[name] = {"description": description or "", "remote": remote, "status": "active",
                 "private": bool(private)}
    if check:
        reg[name]["check"] = check
    reg[name]["reviewed"] = {"date": None, "notes": count_notes(dest)}
    C.save_registry(core, reg)
    commit_registry(core, f"registry: add module {name}")
    C.set_path(core, name, dest)
    C.grant_module_dirs(core)
    print(f"created '{name}' at {dest}" + (f" (copy of {source})" if source else " (bare)"))
    if not description:
        print("  next: replace the template's placeholders, then "
              f"`kc set {name} description=\"what it holds\"`")
    return 0


def add_module(core, name, path, external=False, private=False, description=None, check=None):
    """Register an existing repo. `--external`: not yours — read only, never committed by kc."""
    dest = C.norm_path(path)
    if not G.is_repo(dest):
        raise SystemExit(f"kc add-module: {dest} is not a git repository")
    if name in C.load_registry(core) or name == "core":
        raise SystemExit(f"kc add-module: '{name}' is already registered")
    remote = G.origin_url(dest) or None
    if private and remote and not external:
        problem = G.private_problem(remote)
        if problem:
            raise SystemExit(f"kc add-module: the module is private but {problem}")
    reg = C.load_registry(core)
    entry = {"description": description or describe(dest), "remote": remote, "status": "active",
             "private": bool(private)}
    if external:
        entry["external"] = True
    if check:
        entry["check"] = check
    if not external:
        entry["reviewed"] = {"date": None, "notes": count_notes(dest)}
    reg[name] = entry
    C.save_registry(core, reg)
    commit_registry(core, f"registry: add {'external ' if external else ''}module {name}")
    C.set_path(core, name, dest)
    C.grant_module_dirs(core)
    print(f"registered '{name}' ({'external' if external else 'own'}) -> {dest}")
    if not external and G.branch(dest) != G.BRANCH:
        print(f"  note: kc syncs own modules on '{G.BRANCH}' only; this repo is on '{G.branch(dest)}'")
    if not remote:
        print("  no origin: the module stays on this device until `kc set NAME remote=URL`")
    return 0
