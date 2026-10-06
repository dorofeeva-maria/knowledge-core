"""kc new-module / kc templates — create a module (optionally from a template) and register it.

Module creation is user-driven (the assistant only proposes, per the emergence skill). The
chosen template, if any, becomes the module's `upstream` remote and is recorded in the registry
so other devices can restore it (ADR 0003). Content lives on `main`.
"""
import subprocess
from pathlib import Path
from . import core as C


def list_templates(core):
    """Engine defaults (config/templates.yml) overlaid by the core's own (ecosystem/templates.yml)."""
    out = {}
    for f in (core / "config" / "templates.yml", core / "ecosystem" / "templates.yml"):
        if f.exists():
            out.update((C._yaml().safe_load(f.read_text(encoding="utf-8")) or {}).get("templates") or {})
    return out


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
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def new_module(core, name, template=None, template_url=None, no_template=False, path=None,
               remote=None, language=None, private=False, media=None, check=None,
               description=None):
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
            check = check or t.get("check")
        if not source:
            raise SystemExit("kc new-module: choose --template NAME, --template-url URL, or --no-template")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if source:
        r = subprocess.run(["git", "clone", source, str(dest)], capture_output=True, text=True, encoding="utf-8", errors="replace")
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
        (dest / ".gitignore").write_text("media/large/\n", encoding="utf-8", newline="\n")
        _git(dest, "add", "AGENTS.md", ".gitignore")
        _git(dest, "commit", "-m", "Initialize module")
        print(f"created bare module -> {dest}")

    from .gitsync import prepare, push
    prepare(dest)
    if remote:
        _git(dest, "remote", "add", "origin", remote)
        print(f"  origin -> {remote}: {push(dest)}")
    from .repos import module_description
    _register(core, name, source, remote=remote, language=language, private=private, media=media,
              check=check, description=description or module_description(dest))
    from .gitsync import auto_commit
    auto_commit(core, ["ecosystem/registry.yml"], f"register module {name}")
    _set_path(core, name, dest)
    print(f"registered '{name}' and recorded its path for this device")


def _register(core, name, upstream=None, remote=None, language=None, private=False, media=None,
              check=None, description=None):
    yaml = C._yaml()
    f = core / "ecosystem" / "registry.yml"
    data = (yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}) or {}
    mods = data.get("modules") or {}
    entry = {"description": description or "", "remote": remote, "upstream": upstream, "external": False,
             "status": "active", "private": bool(private)}
    if language:
        entry["language"] = language
    if check:
        entry["check"] = check
    if media is not None:
        entry["media"] = False if media in ("none", "false", "") else media
    mods.setdefault(name, entry)
    data["modules"] = mods
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")


def add_module(core, name, path, external=False, write_zones=(), upstream=None, language=None,
               private=False, media=None, check=None, description=None):
    """Register an existing repo as a module (ADR 0009). Its remote is read from `origin`, its
    template from an existing `upstream` remote unless given. Reports contract problems."""
    from .gitsync import is_repo, remotes, contract, auto_commit, prepare
    dest = Path(path).expanduser().resolve()
    if not is_repo(dest):
        raise SystemExit(f"kc add-module: {dest} is not a git repository")
    if name in C.load_registry(core):
        raise SystemExit(f"kc add-module: '{name}' is already registered")
    rs = remotes(dest)
    remote = _git(dest, "remote", "get-url", "origin").stdout.strip() if "origin" in rs else None
    if not upstream and "upstream" in rs and not external:
        upstream = _git(dest, "remote", "get-url", "upstream").stdout.strip()
    if not external:
        prepare(dest)
    from .repos import module_description
    _register(core, name, upstream, remote=remote, language=language, private=private,
              media=media, check=check, description=description or module_description(dest))
    if external:
        yaml = C._yaml()
        f = core / "ecosystem" / "registry.yml"
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        data["modules"][name].update(external=True, write_zones=list(write_zones))
        data["modules"][name].pop("upstream", None)
        f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    auto_commit(core, ["ecosystem/registry.yml"], f"add module {name}")
    _set_path(core, name, dest)
    print(f"registered existing repo '{name}' ({'external' if external else 'own'}) -> {dest}")
    if not remote:
        print("  no origin: the module stays on this device until it gets a remote")
    if not external:
        for problem in contract(dest, remote, upstream):
            print(f"  MISMATCH: {problem} — fix it, or re-add the module as external")


SETTABLE = {"description", "remote", "status", "private", "external", "write_zones", "language", "media", "check"}


def set_fields(core, name, pairs):
    """`kc set NAME key=value ...` — change registry fields of a module, with side effects
    (ADR 0010): `remote` also points the module's `origin` at it and pushes. Values: `~` or
    `none` clear a field; `true`/`false`; `write_zones` is comma-separated."""
    from .gitsync import is_repo, remotes, push, auto_commit
    yaml = C._yaml()
    f = core / "ecosystem" / "registry.yml"
    data = (yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}) or {}
    mods = data.get("modules") or {}
    if name not in mods:
        raise SystemExit(f"kc set: no module '{name}' in registry")
    entry = mods[name] or {}
    changes = []
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"kc set: expected key=value, got '{pair}'")
        k, v = pair.split("=", 1)
        if k not in SETTABLE:
            raise SystemExit(f"kc set: '{k}' cannot be set (settable: {', '.join(sorted(SETTABLE))}; "
                             f"template: `kc detach`)")
        if v.lower() in ("~", "none", "null"):
            val = None
        elif v.lower() in ("true", "false"):
            val = v.lower() == "true"
        elif k == "write_zones":
            val = [z.strip() for z in v.split(",") if z.strip()]
        else:
            val = v
        if k == "status" and val not in ("active", "frozen", "disconnected"):
            raise SystemExit("kc set: status must be active | frozen | disconnected")
        entry[k] = val
        changes.append(f"{k}={v}")
    mods[name] = entry
    data["modules"] = mods
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    auto_commit(core, ["ecosystem/registry.yml"], f"set {name}: {', '.join(changes)}")
    print(f"set {name}: {', '.join(changes)}")
    path = next((m["path"] for m in C.resolve(core)[0] if m["name"] == name), None)
    if any(c.startswith("remote=") for c in changes) and path and is_repo(path) and not entry.get("external"):
        remote = entry.get("remote")
        if remote:
            verb = "set-url" if "origin" in remotes(path) else "add"
            _git(path, "remote", verb, "origin", remote)
            print(f"  origin -> {remote}: {push(path)}")
        elif "origin" in remotes(path):
            _git(path, "remote", "remove", "origin")
            print("  origin removed: the module is local-only now")


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
