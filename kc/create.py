"""kc new-module / kc templates — create a module (optionally from a template) and register it.

Module creation is user-driven (the assistant only proposes, per the emergence skill). The
chosen template, if any, becomes the module's `upstream` remote and is recorded in the registry
so other devices can restore it (ADR 0003). Content lives on `main`.
"""
import subprocess
from pathlib import Path
from . import core as C


def list_templates(core):
    f = core / "ecosystem" / "templates.yml"
    if not f.exists():
        return {}
    return (C._yaml().safe_load(f.read_text(encoding="utf-8")) or {}).get("templates") or {}


def show_templates(core):
    t = list_templates(core)
    if not t:
        print("templates: none in catalog")
        return
    w = max(len(k) for k in t)
    for name, m in t.items():
        m = m or {}
        print(f"  {name.ljust(w)}  {m.get('source', '?')}")
        if m.get("when"):
            print(f"  {' ' * w}  {m['when']}")


def _git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)


def new_module(core, name, template=None, template_url=None, no_template=False, path=None):
    dest = Path(path).expanduser() if path else (core.parent / "projects" / name)
    if dest.exists():
        raise SystemExit(f"kc new-module: {dest} already exists")

    source = None
    if not no_template:
        source = template_url
        if not source and template:
            t = list_templates(core).get(template)
            if not t:
                raise SystemExit(f"kc new-module: no template '{template}' in catalog (see `kc templates`)")
            source = t.get("source")
        if not source:
            raise SystemExit("kc new-module: choose --template NAME, --template-url URL, or --no-template")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if source:
        r = subprocess.run(["git", "clone", source, str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"kc new-module: clone failed: {r.stderr.strip()}")
        _git(dest, "remote", "rename", "origin", "upstream")
        if _git(dest, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != "main":
            _git(dest, "branch", "-m", "main")
        _git(dest, "branch", "--unset-upstream")
        print(f"forked {source} -> {dest} (template = upstream, content on 'main')")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        _git(dest, "init", "-b", "main")
        (dest / "AGENTS.md").write_text(
            f"# {name} — module instructions\n\n"
            f"A self-contained module. Describe its purpose, structure, and rules here.\n"
            f"Notes use YAML frontmatter (title, type, updated); links are intra-module only.\n",
            encoding="utf-8", newline="\n")
        _git(dest, "add", "AGENTS.md")
        _git(dest, "commit", "-m", "Initialize module")
        print(f"created bare module -> {dest}")

    from .gitsync import prepare
    prepare(dest)
    _register(core, name, source)
    if (core / ".git").exists() and _git(core, "status", "--porcelain", "ecosystem/registry.yml").stdout.strip():
        _git(core, "add", "ecosystem/registry.yml")
        _git(core, "commit", "-m", f"register module {name}")
    _set_path(core, name, dest)
    print(f"registered '{name}' and recorded its path for this device")


def _register(core, name, upstream=None):
    yaml = C._yaml()
    f = core / "ecosystem" / "registry.yml"
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    mods = data.get("modules") or {}
    mods.setdefault(name, {"remote": None, "upstream": upstream, "external": False,
                           "status": "active", "private": False})
    data["modules"] = mods
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")


def _set_path(core, name, dest):
    yaml = C._yaml()
    did = C.load_env(core).get("KC_DEVICE_ID")
    if not did:
        print("  (KC_DEVICE_ID unset — path not recorded; run kc bootstrap)")
        return
    f = core / "ecosystem" / "devices.local.yml"
    data = (yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}) or {}
    data.setdefault(did, {}).setdefault("paths", {})[name] = str(dest)
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
