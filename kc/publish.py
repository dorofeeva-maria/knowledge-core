"""kc publish — copy the engine files of this core into its public engine repo, check them for
personal content, commit and push (the core is where the engine is developed; the public repo is
a snapshot of it, and nothing flows back).

Settings in `ecosystem/instance.yml`:

    publish:
      remote: https://github.com/you/knowledge-core.git   # the public engine repo
      deny: [Alice, Springfield]                         # case-insensitive regexes: personal words

Besides `deny`, the name of every registered module that contains a `-` (e.g. `notes-garden`)
counts as personal. Any hit stops the publish before anything is committed.
"""
import datetime
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from . import core as C
from . import git as G

# What the engine is: everything else in the core (state in ecosystem/) is personal.
ENGINE_DIRS = ("kc", "config", "docs")
ENGINE_FILES = (".claude/settings.json", ".gitattributes", ".gitignore", "AGENTS.md", "CLAUDE.md",
                "README.md", "CHANGELOG.md", "ecosystem/README.md")
SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store)(/|$)|\.pyc$")


def engine_files(root):
    """Relative paths (posix) of the engine files present under root."""
    root = Path(root)
    out = [f for f in ENGINE_FILES if (root / f).is_file()]
    for d in ENGINE_DIRS:
        for p in sorted((root / d).rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and not SKIP.search(rel):
                out.append(rel)
    return sorted(out)


def _patterns(core):
    pub = (C.load_instance(core) or {}).get("publish") or {}
    pats = []
    for w in pub.get("deny") or []:
        try:
            pats.append((str(w), re.compile(str(w), re.I)))
        except re.error as e:
            raise SystemExit(f"kc publish: bad pattern in instance.yml publish.deny: {w!r} ({e})")
    for name in C.load_registry(core):
        if "-" in name:
            pats.append((name, re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", re.I)))
    return pub.get("remote"), pats


def scan(root, files, pats):
    """[(file, line no, pattern, line)] for every personal word found."""
    hits = []
    for rel in files:
        try:
            text = (Path(root) / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for no, line in enumerate(text.splitlines(), 1):
            for label, rx in pats:
                if rx.search(line):
                    hits.append((rel, no, label, line.strip()[:100]))
    return hits


def run(core, remote=None, message=None, dry_run=False):
    configured, pats = _patterns(core)
    remote = remote or configured
    if not remote:
        raise SystemExit("kc publish: no target — set publish.remote in ecosystem/instance.yml "
                         "(or pass --remote URL)")
    if G.same_url(remote, G.origin_url(core) if G.has_origin(core) else ""):
        raise SystemExit("kc publish: the target is this core's own origin — refusing")
    files = engine_files(core)
    dirty = G.git(core, "status", "--porcelain", "--", *ENGINE_DIRS, *ENGINE_FILES).stdout.strip()
    if dirty:
        raise SystemExit("kc publish: engine files have uncommitted changes — commit them first:\n" + dirty)

    hits = scan(core, files, pats)
    if hits:
        print("kc publish: personal content in engine files — nothing published. Fix it in the core:")
        for rel, no, label, line in hits:
            print(f"  {rel}:{no}  [{label}]  {line}")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="kc-publish-"))
    try:
        dest = tmp / "engine"
        r = subprocess.run(["git", *G.LONGPATHS, "clone", "--quiet", remote, str(dest)])
        if r.returncode != 0:
            raise SystemExit(f"kc publish: could not clone {remote}")
        old = set(engine_files(dest))
        for rel in old - set(files):
            (dest / rel).unlink()
        for rel in files:
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(core / rel, dest / rel)
        G.git(dest, "add", "-A")
        changed = G.git(dest, "status", "--porcelain").stdout.rstrip()
        if not changed:
            print(f"kc publish: {remote} already has this engine — nothing to publish")
            return 0
        print(f"kc publish → {remote}")
        for line in changed.splitlines():
            print("  " + line)
        smoke = subprocess.run([sys.executable, "-m", "kc", "--help"], cwd=dest,
                               capture_output=True, text=True)
        if smoke.returncode != 0:
            print("kc publish: `python -m kc --help` fails in the published copy — nothing published")
            print(smoke.stderr[-2000:])
            return 1
        if dry_run:
            print("dry run: nothing committed or pushed")
            return 0
        msg = message or f"release {datetime.date.today().isoformat()}"
        c = G.git(dest, "commit", "-q", "-m", msg)
        if c.returncode != 0:
            raise SystemExit(f"kc publish: commit failed: {c.stderr.strip()}")
        p = G.git(dest, "push", "-q", "origin", "HEAD")
        if p.returncode != 0:
            raise SystemExit(f"kc publish: push failed: {p.stderr.strip()}")
        print(f"published: {G.git(dest, 'log', '--oneline', '-1').stdout.strip()}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
