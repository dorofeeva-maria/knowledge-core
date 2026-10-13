"""Template updates: `kc template-update`, `kc template-bind` (ADR 0016).

A template owns some files of the modules made from it — the `owned` patterns of its catalog
entry (fnmatch, `*` also crosses `/`). Everything else belongs to the module. An update copies
the template's new versions of owned files into each module, file by file:

- the module's file still equals the template's version it came from → replaced (or removed);
- a file new in the template → added;
- the module changed the file itself → left alone; reported ("kept local") only while the
  template has a change to it since the recorded version that the file does not contain yet —
  until then the recorded version is not advanced, so the pending merge stays visible;
- the file equals a past template version and was last changed by the template → just behind,
  updated (see `plan`).

No merge or rebase between repos; a module's history is never rewritten. The registry records
each module's `template` and `template_version` (the template commit its owned files came from).
"""
import fnmatch
import hashlib
import os
import unicodedata
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from . import core as C
from . import git as G
from .registry import commit_registry


def _git_bytes(path, *args):
    r = subprocess.run(["git", *G.LONGPATHS, "-C", str(path), *args], capture_output=True, env=G._ENV)
    return r.stdout if r.returncode == 0 else None


def _norm(data):
    """Compare text the way git stores it (LF); binary as is."""
    if data is None or b"\0" in data[:8000]:
        return data
    return data.replace(b"\r\n", b"\n")


def owned_patterns(entry):
    return [p for p in ((entry or {}).get("owned") or []) if isinstance(p, str) and p.strip()]


def is_owned(rel, patterns):
    return any(fnmatch.fnmatchcase(rel, p) for p in patterns)


@contextmanager
def clone(source):
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["git", "clone", "--quiet", source, tmp], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=G._ENV, timeout=G.NET_TIMEOUT)
        if r.returncode != 0:
            raise SystemExit(f"kc: cannot fetch template {source}: {G.first(r.stderr)}")
        yield Path(tmp)


def head(repo):
    return G.git(repo, "rev-parse", "HEAD").stdout.strip()


def _known(repo, ver):
    return bool(ver) and G.git(repo, "cat-file", "-e", f"{ver}^{{commit}}").returncode == 0


def _tree(repo, ver, patterns):
    names = G.git(repo, "ls-tree", "-r", "--name-only", "-z", ver).stdout.split("\0")
    return {n for n in names if n and is_owned(n, patterns)}


def _module_files(path, patterns):
    """Owned paths the module tracks in git (ignored or untracked files — .DS_Store,
    __pycache__ — are not the module's version of anything)."""
    names = G.git(path, "-c", "core.quotePath=false", "ls-files", "-z").stdout.split("\0")
    return {n for n in names if n and is_owned(n, patterns)}


def _ignored(path, rels):
    """Which of `rels` the module's .gitignore excludes: never written, never committed."""
    if not rels:
        return set()
    r = subprocess.run(["git", *G.LONGPATHS, "-C", str(path), "check-ignore", "--no-index", "-z", "--stdin"],
                       input="\0".join(rels).encode("utf-8"), capture_output=True, env=G._ENV)
    return {n for n in r.stdout.decode("utf-8", "replace").split("\0") if n}


def plan(repo, base, new, mpath, patterns, template=None):
    """Per owned path: ('update'|'add'|'remove'|'local'|'ignored'|'collision', path). Unchanged
    paths are left out; 'ignored' = the template has it but the module's .gitignore excludes it
    (skipped); 'collision' = its name equals another file's up to letter case or Unicode form —
    one file on macOS/Windows — so it is not touched (skipped, done by hand).
    A file whose content equals a version the template once had at that path, and which the
    module last changed through the template itself (an update commit or its creation from the
    template), is not a local edit — the module is just behind (a resolved race, a stale or
    unknown base) — so it is updated. If the module's own commit put it there (pinning an old
    version, restoring a dropped file), it is the module's decision and kept. A file missing from the module is added unless the module itself once tracked and
    deleted it. base None = unknown origin."""
    have = _module_files(mpath, patterns)
    in_new = _tree(repo, new, patterns)
    in_base = _tree(repo, base, patterns) if base else set()
    ignored = _ignored(mpath, sorted(in_new - have))
    actions = [("ignored", rel) for rel in sorted(ignored)]
    for rel in sorted((have | in_new | in_base) - ignored):
        cur = _norm((Path(mpath) / rel).read_bytes()) if rel in have else None
        nxt = _norm(_git_bytes(repo, "show", f"{new}:{rel}")) if rel in in_new else None
        if cur == nxt:
            continue
        old = _norm(_git_bytes(repo, "show", f"{base}:{rel}")) if (base and rel in in_base) else None
        if cur is None:
            if nxt is not None and not _module_deleted(mpath, rel):
                actions.append(("add", rel))
            continue                       # the module deleted it on purpose: leave it deleted
        if (base and cur == old) or (_last_change_by_template(mpath, rel, template)
                                      and _was_template_version(repo, rel, cur)):
            actions.append(("update" if nxt is not None else "remove", rel))
        else:
            actions.append(("local", rel))
    return _collisions(mpath, actions)


def _last_change_by_template(mpath, rel, template):
    """Was `rel` last changed in the module by the template — a `template-update` commit
    ("template T …") or the module's creation from the template ("Start NAME from template T")?"""
    if not template:
        return False
    subject = G.git(mpath, "log", "-1", "--format=%s", "--", rel).stdout.strip()
    return subject.startswith(f"template {template} ") or (
        subject.startswith("Start ") and subject.endswith(f" from template {template}"))


def _template_change_pending(repo, base, new, mpath, rel):
    """For a file the module changed itself ('local'): is there a change of the template since
    `base` still to bring in? No if the template did not change it since base, or if a 3-way
    merge of the template's change into the module's file changes nothing (already brought in
    by hand). Unknown base: can't tell — yes."""
    if not base:
        return True
    old = _norm(_git_bytes(repo, "show", f"{base}:{rel}"))
    nxt = _norm(_git_bytes(repo, "show", f"{new}:{rel}"))
    if old == nxt:
        return False
    cur = _norm((Path(mpath) / rel).read_bytes())
    if old is None or nxt is None:
        return True
    with tempfile.TemporaryDirectory() as d:
        files = []
        for n, data in (("module", cur), ("base", old), ("template", nxt)):
            (Path(d) / n).write_bytes(data)
            files.append(str(Path(d) / n))
        r = subprocess.run(["git", "merge-file", "-p", "--quiet", *files], capture_output=True, env=G._ENV)
    return not (r.returncode == 0 and _norm(r.stdout) == cur)


def _module_deleted(mpath, rel):
    """The module once tracked `rel` and removed it: its own decision."""
    return bool(G.git(mpath, "log", "-1", "--format=%H", "--", rel).stdout.strip())


def _was_template_version(repo, rel, content):
    """Does `content` equal the template's file at `rel` in any commit of its history?"""
    r = subprocess.run(["git", *G.LONGPATHS, "-C", str(repo), "hash-object", "--stdin"],
                       input=content, capture_output=True, env=G._ENV)
    sha = r.stdout.decode().strip()
    if not sha:
        return False
    raw = G.git(repo, "log", "--all", "--format=", "--raw", "--no-abbrev", "--no-renames", "--", rel).stdout
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 4 and line.startswith(":") and sha in (parts[2], parts[3]):
            return True
    return False


def _fold(name):
    return unicodedata.normalize("NFC", name).casefold()


def _dirs(rel):
    parts = rel.split("/")[:-1]
    return ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def _collisions(mpath, actions):
    """An added path whose name folds to a file the module already has (or to another path of
    this update) is one file on case-insensitive disks: writing it would overwrite that file, and
    a case-only rename would delete it. Likewise a folder of it spelled differently from a folder
    the module has (`artifacts/` vs `Artifacts/`): the file would land in that folder under a name
    git cannot commit or roll back. Such paths — and their partners in this update — are skipped
    and reported instead."""
    tracked = [n for n in G.git(mpath, "-c", "core.quotePath=false", "ls-files", "-z").stdout.split("\0") if n]
    by_fold, dirs = {}, {}
    for n in tracked:
        by_fold.setdefault(_fold(n), set()).add(n)
        for d in _dirs(n):
            dirs.setdefault(_fold(d), set()).add(d)
    hit = set()
    adds = [r for k, r in actions if k == "add"]
    seen = {}
    for r in adds:
        f = _fold(r)
        others = (by_fold.get(f, set()) | seen.get(f, set())) - {r}
        if others:
            hit.add(r)
            hit |= others
        seen.setdefault(f, set()).add(r)
    for r in adds:                                  # folders: the module's and the adds' own
        for d in _dirs(r):
            dirs.setdefault(_fold(d), set()).add(d)
    for r in adds:
        if any(dirs.get(_fold(d), set()) - {d} for d in _dirs(r)):
            hit.add(r)
    if not hit:
        return actions
    out = [(k, r) for k, r in actions if r not in hit]
    return out + [("collision", r) for r in sorted(hit)]


def _rollback(mpath, actions, created):
    """Put the module back exactly as it was (it was clean before the update): tracked paths from
    HEAD; only files this run created from nothing are deleted."""
    tracked = [r for k, r in actions if k in ("update", "remove")]
    paths = tracked + [r for k, r in actions if k == "add"]
    if paths:
        G.git(mpath, "reset", "-q", "--", *paths)
    if tracked:
        G.git(mpath, "checkout", "-q", "HEAD", "--", *tracked)
    for rel in created:
        f = Path(mpath) / rel
        if os.path.lexists(f) and not f.is_dir():
            f.unlink()


def _apply(repo, new, mpath, actions, created):
    """Write the planned changes. `created` collects the files that did not exist before (by any
    spelling), the only ones a rollback may delete."""
    touched = []
    for kind, rel in actions:
        dest = Path(mpath) / rel
        if kind in ("update", "add"):
            existed = os.path.lexists(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = _git_bytes(repo, "show", f"{new}:{rel}")
            if data is None:
                raise RuntimeError(f"cannot read {rel} from the template")
            if not existed:
                created.append(rel)
            dest.write_bytes(data)
            touched.append(rel)
        elif kind == "remove":
            dest.unlink()
            touched.append(rel)
    return touched


def _template_entry(core, name):
    from .modules import list_templates
    t = list_templates(core).get(name)
    if not t or not t.get("source"):
        raise SystemExit(f"kc: no template '{name}' in the catalog (see `kc templates`)")
    if not owned_patterns(t):
        raise SystemExit(f"kc: template '{name}' declares no `owned` files in the catalog — "
                         f"add them to ecosystem/templates.yml first")
    return t


def _targets(core, template, only=None):
    out = []
    reg = C.load_registry(core)
    for m in C.modules(core):
        e = reg.get(m["name"]) or {}
        if e.get("template") != template or (only and m["name"] != only):
            continue
        if m["external"] or m["status"] == "frozen":
            continue
        out.append((m, e))
    return out


def update(core, template, only=None, dry_run=False, diff=False):
    t = _template_entry(core, template)
    patterns = owned_patterns(t)
    targets = _targets(core, template, only)
    if not targets:
        print(f"template-update: no active module is bound to template '{template}'"
              + (f" under the name '{only}'" if only else "") + " (see `kc template-bind`)")
        return 1
    reg = C.load_registry(core)
    failed, changed_reg = False, False
    with clone(t["source"]) as repo:
        new = head(repo)
        print(f"template {template}: {t['source']} @ {new[:7]}")
        bases = []
        for m, e in targets:
            name, path = m["name"], m["path"]
            base = e.get("template_version")
            label = f"  {name}"
            if not (path and path.exists()):
                print(f"{label}: not set up on this device — skipped")
                continue
            if G.dirty(path):
                print(f"{label}: FAIL uncommitted changes — commit or sync first")
                failed = True
                continue
            if base and not _known(repo, base):
                print(f"{label}: recorded version {base[:7]} is not in the template's history — "
                      f"treated as unknown")
                base = None
            actions = plan(repo, base, new, path, patterns, template)
            # a module's own edit with nothing new from the template needs no action: not listed
            local = [r for k, r in actions if k == "local"
                     and _template_change_pending(repo, base, new, path, r)]
            if base == new and not any(k in ("update", "add", "remove") for k, _ in actions):
                clash = [r for k, r in actions if k == "collision"]
                print(f"{label}: up to date" + (f" (name clash: {', '.join(clash)})" if clash else ""))
                continue
            bases.append(base)
            skipped = [r for k, r in actions if k == "ignored"]
            clashes = [r for k, r in actions if k == "collision"]
            moves = [(k, r) for k, r in actions if k in ("update", "add", "remove")]
            counts = [(sum(1 for k, _ in moves if k == x), word) for x, word in
                      (("update", "updated"), ("add", "added"), ("remove", "removed"))]
            summary = ", ".join(f"{n} {w}" for n, w in counts if n) or "no file changes"
            print(f"{label}: {(base or 'unknown')[:7]} → {new[:7]}: {summary}")
            for k, r in moves:
                print(f"      {k:6} {r}")
            for r in local:
                print(f"      KEPT LOCAL {r} — the module changed it and so did the template; bring the "
                      f"template's change in by hand")
            for r in skipped:
                print(f"      IGNORED    {r} — the module's .gitignore excludes it; not copied")
            for r in clashes:
                print(f"      NAME CLASH {r} — same name (or folder) up to letter case/Unicode form as another file; "
                      f"not touched — rename by hand (git mv) with the human")
            hold = bool(base and (local or clashes))   # pending merges stay visible: every run
            if hold:                                   # and the start signal list them until done
                print(f"      registry keeps {base[:7]} for {name} until the files above are resolved by hand"
                      + (f" (a KEPT LOCAL file merged with edits of the module's own stays listed — once "
                         f"done, record it: kc template-bind {name} {template} --version {new[:7]})"
                         if local else ""))
            if dry_run:
                continue
            created = []
            try:
                touched = _apply(repo, new, path, moves, created)
                if touched:
                    log = G.git(repo, "log", "--format=- %h %s", f"{base}..{new}" if base else "-5", new).stdout
                    msg = (f"template {template} {(base or 'unknown')[:7]} → {new[:7]}: {summary}"
                           + (f"; kept local: {', '.join(local)}" if local else "")
                           + "\n\nTemplate changes:\n" + log)
                    a = G.git(path, "add", "-A", "--", *touched)
                    r = a if a.returncode != 0 else G.git(path, "commit", "-q", "-m", msg, "--", *touched)
                    if r.returncode != 0:
                        raise RuntimeError(" ".join(((r.stderr or "") + " " + (r.stdout or "")).split())[:300]
                                           or "git refused the commit")
            except Exception as ex:          # leave the module exactly as it was
                _rollback(path, moves, created)
                print(f"      FAIL {ex} — module restored, nothing changed; registry keeps {(base or 'unknown')[:7]}")
                failed = True
                continue
            if hold:
                continue
            reg[name] = {**(reg[name] or {}), "template_version": new}
            changed_reg = True
        _report_unowned(repo, bases, new, patterns, diff)
    if changed_reg:
        C.save_registry(core, reg)
        commit_registry(core, f"registry: template {template} → {new[:7]} in "
                              + ", ".join(m["name"] for m, _ in targets if reg[m["name"]].get("template_version") == new))
    if dry_run:
        print("dry run: nothing written")
    else:
        print("next: pushed by `kc sync` (or the session-end hook)")
    return 1 if failed else 0


def _report_unowned(repo, bases, new, patterns, diff):
    """Files the template changed that it doesn't own (AGENTS.md…): listed for the agent to carry
    over by judgment, never copied."""
    known = [b for b in bases if b]
    if not known:
        if bases:
            print("  not owned by the template: modules of unknown origin — compare AGENTS.md etc. by hand")
        return
    oldest = known[0]
    for b in known[1:]:
        if G.git(repo, "merge-base", "--is-ancestor", b, oldest).returncode == 0:
            oldest = b
    names = [n for n in G.git(repo, "diff", "--name-only", oldest, new).stdout.splitlines()
             if n and not is_owned(n, patterns)]
    if not names:
        return
    print(f"  also changed in the template since {oldest[:7]}, not owned (carry over by hand where it fits):")
    for n in names:
        print(f"      {n}")
    if diff:
        print(G.git(repo, "diff", oldest, new, "--", *names).stdout)
    else:
        print("      (add --diff to see the changes)")


def bind(core, name, template, version=None):
    """Record which template (and which of its commits) a module's owned files came from. Without
    --version: the newest template commit whose owned files differ least from the module's."""
    reg = C.load_registry(core)
    if name not in reg:
        raise SystemExit(f"kc template-bind: no module '{name}' in registry")
    m = next(x for x in C.modules(core) if x["name"] == name)
    if not (m["path"] and m["path"].exists()):
        raise SystemExit(f"kc template-bind: '{name}' is not set up on this device")
    t = _template_entry(core, template)
    patterns = owned_patterns(t)
    with clone(t["source"]) as repo:
        if version:
            if not _known(repo, version):
                raise SystemExit(f"kc template-bind: {version} is not a commit of template '{template}'")
            best = G.git(repo, "rev-parse", f"{version}^{{commit}}").stdout.strip()
            diffs = [r for k, r in plan(repo, best, best, m["path"], patterns, template)]
        else:
            best = _closest(repo, m["path"], patterns)
            diffs = [r for k, r in plan(repo, best, best, m["path"], patterns, template)]
    reg[name] = {**(reg[name] or {}), "template": template, "template_version": best}
    C.save_registry(core, reg)
    commit_registry(core, f"registry: {name} bound to template {template} @ {best[:7]}")
    print(f"bound {name} → template {template} @ {best[:7]}"
          + (f"; {len(diffs)} owned file(s) differ (an update will keep them as local edits):"
             if diffs else "; owned files match exactly"))
    for r in diffs or []:
        print(f"      {r}")
    return 0


def _closest(repo, mpath, patterns):
    """The newest template commit whose owned files differ from the module's in the fewest paths
    (counted as `plan` counts them). Compares content digests — one ls-tree per commit, each
    template blob read once — so a long history stays fast."""
    have = _module_files(mpath, patterns)
    mine = {rel: hashlib.sha1(_norm((Path(mpath) / rel).read_bytes())).digest() for rel in have}
    trees = []
    for ver in G.git(repo, "rev-list", "HEAD").stdout.split():
        tree = {}
        for line in G.git(repo, "-c", "core.quotePath=false", "ls-tree", "-r", "-z", ver).stdout.split("\0"):
            meta, _, rel = line.partition("\t")
            if rel and meta.split()[1:2] == ["blob"] and is_owned(rel, patterns):
                tree[rel] = meta.split()[2]
        trees.append((ver, tree))
    blobs = {}
    for b in {b for _, t in trees for b in t.values()}:
        blobs[b] = hashlib.sha1(_norm(_git_bytes(repo, "cat-file", "blob", b)) or b"").digest()
    missing = sorted({r for _, t in trees for r in t} - have)
    ignored = _ignored(mpath, missing)
    skip = {r for r in missing if r not in ignored and _module_deleted(mpath, r)}   # plan leaves these out
    best, fewest = None, None
    for ver, tree in trees:
        n = sum(1 for r in have | set(tree) if r not in skip
                and (r not in tree or r not in have or blobs[tree[r]] != mine[r]))
        if fewest is None or n < fewest:
            best, fewest = ver, n
        if not n:
            break
    return best


def signals(core, seconds=40):
    """Templates with a newer commit than some of their modules (network: one ls-remote per
    template, all within `seconds`; a template not reached in time is skipped). For the
    session-start hook only; never writes."""
    import time
    end = time.monotonic() + seconds
    from .modules import list_templates
    reg = C.load_registry(core)
    present = {m["name"] for m in C.modules(core)
               if m["path"] and m["path"].exists() and not m["external"] and m["status"] != "frozen"}
    by_t = {}
    for name, e in reg.items():
        e = e or {}
        if name in present and e.get("template"):
            by_t.setdefault(e["template"], []).append((name, e.get("template_version")))
    rows = []
    cat = list_templates(core)
    for tname, mods in sorted(by_t.items()):
        src = (cat.get(tname) or {}).get("source")
        if not src or not owned_patterns(cat.get(tname)):
            continue
        left = end - time.monotonic()
        if left < 3:
            break
        r = G.git(".", "ls-remote", src, "HEAD", timeout=min(20, int(left)))
        if r.returncode != 0 or not r.stdout.strip():
            continue
        sha = r.stdout.split()[0]
        behind = [n for n, v in mods if v != sha]
        if behind:
            rows.append(("template", f"{tname} @ {sha[:7]} is ahead of {len(behind)} module(s) "
                                     f"({', '.join(behind)}) — show `kc template-update {tname} --dry-run` "
                                     f"to the human; run it on a yes"))
    return rows
