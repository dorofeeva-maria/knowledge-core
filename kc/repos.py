"""Cross-repo mechanical ops: registry view, HOME, pull-all / update / detach, commit-push,
push-all.

Deterministic plumbing the skills (and the session-start hook) call. Git mechanics live in
gitsync.py. Pushing is opt-in (`--push` / `push-all`) so nothing leaves the machine without an
explicit decision.
"""
from pathlib import Path
from . import core as C
from . import maintain
from . import gitsync as G


def _repo_root(path):
    r = G.git(path, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def _print_report(report):
    w = max((len(n) for n, _ in report), default=4)
    for n, s in report:
        print(f"  {n.ljust(w)}  {s}")


# ---------------------------------------------------------------- registry
def show_registry(core):
    mods, did = C.resolve(core)
    print(f"core: {core}")
    print(f"device: {did or '(KC_DEVICE_ID unset)'}")
    if not mods:
        print("modules: none in registry")
        return
    w = max(len(m["name"]) for m in mods)
    for m in mods:
        here = "here" if (m["path"] and m["path"].exists()) else ("absent" if m["path"] else "no-path")
        flags = [m["status"]] + (["external"] if m["external"] else []) + (["private"] if m["private"] else [])
        print(f"  {m['name'].ljust(w)}  {here:7}  {' '.join(flags)}")


# ---------------------------------------------------------------- HOME map
def _module_desc(path):
    if not path or not Path(path).exists():
        return ""
    for fn in ("overview.md", "README.md", "AGENTS.md"):
        f = Path(path) / fn
        if f.exists():
            s = maintain.summary_line(f.read_text(encoding="utf-8", errors="replace"))
            if s:
                return s
    return ""


def home(core):
    mods, _ = C.resolve(core)
    active = [m for m in mods if m["status"] != "disconnected"]
    lines = ["<!-- auto-generated map of modules; regenerate with `kc home` -->", "", "# HOME", ""]
    if not active:
        lines.append("_No modules yet._")
    for m in active:
        flags = ([m["status"]] if m["status"] != "active" else []) \
            + (["external"] if m["external"] else []) + (["private"] if m["private"] else [])
        tag = f" _({', '.join(flags)})_" if flags else ""
        desc = _module_desc(m["path"])
        lines.append(f"- **{m['name']}**{tag}" + (f" — {desc}" if desc else ""))
    (core / "ecosystem" / "HOME.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    G.auto_commit(core, ["ecosystem/HOME.md"], "regenerate HOME")
    print(f"home: {len(active)} module(s) mapped")


# ---------------------------------------------------------------- sync (pull)
def _core_upstream(core):
    inst = C.load_instance(core)
    if "upstream" in inst and not inst["upstream"]:
        return G.DETACHED
    return inst.get("upstream")


def _targets(core, include_frozen=True, modules_only=False):
    """[(name, path, external, upstream_url)] for the core + modules present on this device."""
    out = [] if modules_only else [("core", core, False, lambda: _core_upstream(core))]
    for m in C.resolve(core)[0]:
        if m["status"] == "disconnected" or (m["status"] == "frozen" and not include_frozen):
            continue
        out.append((m["name"], m["path"], m["external"], m["upstream"]))
    return [(n, p, ext, G.DETACHED if u == "detached" else u) for n, p, ext, u in out]


def pull_all(core):
    # the core first: its registry may change (new modules, detach) before modules are synced
    report = [("core", G.sync(core, "core", False, lambda: _core_upstream(core)))]
    report += [(n, G.sync(p, n, ext, up)) for n, p, ext, up in _targets(core, modules_only=True)]
    _print_report(report)
    if any("UPDATE" in s or "CONFLICT" in s for _, s in report):
        print("→ template/engine updates found: follow skills/update.md before working in those repos")
    return report


def update(core, name):
    """Interactive sync of one repo: an upstream conflict is left in progress to resolve."""
    for n, p, ext, up in _targets(core):
        if n == name:
            if ext:
                raise SystemExit(f"kc update: '{name}' is external — it has no template updates")
            if G._rebase_in_progress(p):
                files = G._unmerged(p)
                if files:
                    print(f"  {name}: still conflicted: {', '.join(files)}")
                    return 1
                ok, files = G.rebase(p, "rebase", "--continue")
                print(f"  {name}: " + ("rebase finished — push with `kc push-all`" if ok
                                       else f"conflicts in {', '.join(files)}"))
                return 0 if ok else 1
            print(f"  {name}: {G.sync(p, name, ext, up, interactive=True)}")
            return 0
    raise SystemExit(f"kc update: no repo '{name}' on this device")


DETACH_WARNING = """Detaching '{name}' from its {what}:
  - it stops receiving {what} updates (rules, structure, fixes) — permanently, unless you
    re-add the upstream by hand;
  - its content stays as is; future {what} changes will not be adapted into it;
  - for the core: skills and kc stop evolving with the engine; you maintain them yourself.
Re-run with --yes to detach."""


def detach(core, name, yes=False):
    is_core = name == "core"
    what = "engine" if is_core else "template"
    if not yes:
        print(DETACH_WARNING.format(name=name, what=what))
        return 1
    path = core if is_core else next((m["path"] for m in C.resolve(core)[0] if m["name"] == name), None)
    if path and G.is_repo(path):
        if G._rebase_in_progress(path):
            G.git(path, "rebase", "--abort")
        if "upstream" in G.remotes(path):
            G.git(path, "remote", "remove", "upstream")
    yaml = C._yaml()
    if is_core:
        f = core / "ecosystem" / "instance.yml"
        data = C.load_instance(core)
        data["upstream"] = None
    else:
        f = core / "ecosystem" / "registry.yml"
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        mods = data.get("modules") or {}
        if name not in mods:
            raise SystemExit(f"kc detach: no module '{name}' in registry")
        mods[name] = {**(mods[name] or {}), "upstream": None}
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    G.auto_commit(core, [f.relative_to(core).as_posix()], f"detach {name} from its {what}")
    print(f"detached '{name}' from its {what} (upstream removed, recorded in {f.name}; "
          f"add the reason to ecosystem/decisions.md)")
    return 0


# ---------------------------------------------------------------- commit / push
def commit_push(core, message, all_repos=False):
    """Commit and push right away (ADR 0006). External modules are committed but never pushed
    here — the human confirms that with `kc push-external NAME`."""
    ext_paths = {Path(p).resolve() for _, p, ext, _ in _targets(core) if ext and p}
    if all_repos:
        targets = [(n, p) for n, p, ext, _ in _targets(core, include_frozen=False) if not ext and p]
    else:
        root = _repo_root(Path.cwd())
        if not root:
            raise SystemExit("kc commit-push: not inside a git repo")
        targets = [(root.name, root)]
    report = []
    for name, path in targets:
        if not G.is_repo(path):
            report.append((name, "absent"))
            continue
        if not G.dirty(path):
            report.append((name, "nothing to commit"))
            continue
        big = G.stage(path, limit=G.large_limit(core))
        if big:
            report.append((name, f"left out (over {G.large_limit(core) // 2**20} MB): {', '.join(big)} — "
                                 f"move to <media>/large/ (not committed)"))
        if not G.git(path, "diff", "--cached", "--quiet").returncode:
            report.append((name, "nothing to commit"))
            continue
        r = G.git(path, "commit", "-m", message)
        if r.returncode != 0:
            report.append((name, f"commit fail: {G.last(r.stderr)}"))
            continue
        if Path(path).resolve() in ext_paths:
            report.append((name, "committed (external: confirm, then `kc push-external NAME`)"))
        else:
            report.append((name, "committed, " + G.push(path)))
    _print_report(report)
    return report


def push_external(core, name):
    for n, p, ext, _ in _targets(core, modules_only=True):
        if n == name:
            if not ext:
                raise SystemExit(f"kc push-external: '{name}' is not external — it is pushed on commit")
            r = G.git(p, "push")
            print(f"  {name}: " + ("pushed" if r.returncode == 0 else f"fail: {G.last(r.stderr)}"))
            return r.returncode
    raise SystemExit(f"kc push-external: no module '{name}' on this device")


def push_all(core):
    report = []
    for name, path, ext, _ in _targets(core, include_frozen=False):
        if ext:
            continue
        report.append((name, G.push(path) if G.is_repo(path) else "absent"))
    _print_report(report)
    return report
