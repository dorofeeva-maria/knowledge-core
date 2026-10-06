"""Git synchronization for the core and its modules (see ADR 0003).

One branch, `main`, holds all content. Two remotes:
  origin   — your own copy of the repo (shared by your devices);
  upstream — the engine (for the core) or the module's template, if it has one.

Sync order on every session start: fetch → rebase onto origin/main (pick up other devices'
work) → rebase onto upstream/main (always apply template/engine updates). Pushes use
--force-with-lease plus an "includes origin" check, because applying an upstream update rewrites history.
External repos are never rebased or pushed: fast-forward only, on whatever branch they use.
"""
import os
import subprocess
from pathlib import Path

BRANCH = "main"
_ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, env=_ENV)


def last(s):
    lines = (s or "").strip().splitlines()
    return lines[-1] if lines else ""


def is_repo(path):
    return bool(path) and (Path(path) / ".git").exists()


def dirty(path):
    return bool(git(path, "status", "--porcelain").stdout.strip())


def remotes(path):
    return git(path, "remote").stdout.split()


def branch(path):
    return git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def has_ref(path, ref):
    return git(path, "rev-parse", "--verify", "--quiet", ref).returncode == 0


def short(path, ref):
    return git(path, "rev-parse", "--short", ref).stdout.strip()


def _rebase_in_progress(path):
    gd = Path(path) / ".git"
    return (gd / "rebase-merge").exists() or (gd / "rebase-apply").exists()


def _unmerged(path):
    return git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()


DETACHED = object()   # config says "no upstream" explicitly (detached or bare)


def prepare(path, upstream_url=None):
    """Idempotent per-repo setup: rerere on; the upstream remote follows the config —
    restored when a URL is recorded, removed when the config says DETACHED (detached on another
    device), left alone when the config does not say (None)."""
    git(path, "config", "rerere.enabled", "true")
    git(path, "config", "rerere.autoupdate", "true")
    rs = remotes(path)
    if upstream_url is DETACHED:
        if "upstream" in rs:
            git(path, "remote", "remove", "upstream")
    elif upstream_url and "upstream" not in rs:
        git(path, "remote", "add", "upstream", upstream_url)


def rebase(path, *args):
    """Run a rebase; let rerere replay remembered resolutions. Returns (ok, conflicted_files).
    On conflict the rebase is left in progress — the caller decides to abort or hand it over."""
    r = git(path, *args)
    while r.returncode != 0 and _rebase_in_progress(path):
        files = _unmerged(path)
        if files:
            return False, files
        r = git(path, "rebase", "--continue")   # rerere resolved everything in this step
    if r.returncode != 0:
        return False, [last(r.stderr) or "rebase failed"]
    return True, []


def sync(path, name, external=False, upstream_url=None, interactive=False):
    """Bring one repo up to date. Returns a one-line status for the report.
    `upstream_url` may be a callable: it is evaluated after the origin rebase, so a config
    change made on another device (e.g. a detach) is seen before upstream is touched."""
    if not is_repo(path):
        return "absent"
    if _rebase_in_progress(path):
        return f"REBASE IN PROGRESS — finish it: `kc update {name}`"
    if dirty(path):
        return "skipped (uncommitted changes)"
    if external:  # not ours: their branches, their history
        r = git(path, "pull", "--ff-only")
        return "ok (ff)" if r.returncode == 0 else f"fail (ff): {last(r.stderr)}"
    b = branch(path)
    if b != BRANCH:
        return f"skipped (on branch '{b}', expected '{BRANCH}')"
    git(path, "fetch", "--all", "--prune", "--quiet")
    msgs = []
    if "origin" in remotes(path) and has_ref(path, f"refs/remotes/origin/{BRANCH}"):
        ok, files = rebase(path, "pull", "--rebase", "origin", BRANCH)
        if not ok:
            git(path, "rebase", "--abort")
            return (f"CONFLICT with origin ({', '.join(files[:3])}) — resolve by hand: "
                    f"git -C {path} pull --rebase origin {BRANCH}")
        msgs.append("origin")
    prepare(path, upstream_url() if callable(upstream_url) else upstream_url)
    git(path, "fetch", "upstream", "--quiet") if "upstream" in remotes(path) else None
    if "upstream" in remotes(path) and has_ref(path, f"refs/remotes/upstream/{BRANCH}"):
        up = f"upstream/{BRANCH}"
        if git(path, "merge-base", "--is-ancestor", up, "HEAD").returncode != 0:
            old = short(path, git(path, "merge-base", "HEAD", up).stdout.strip())
            new = short(path, up)
            ok, files = rebase(path, "rebase", up)
            if not ok:
                if interactive:
                    return (f"UPDATE {old}..{new}: conflicts in {', '.join(files)} — rebase left in "
                            f"progress for you to resolve (see skills/update.md)")
                git(path, "rebase", "--abort")
                return (f"UPDATE CONFLICT {old}..{new} ({', '.join(files[:3])}) — blocked until "
                        f"resolved: `kc update {name}` or `kc detach {name}`")
            msgs.append(f"UPDATE APPLIED {old}..{new} — review for content adaptation: "
                        f"git -C {path} diff {old} {new}")
        else:
            msgs.append("upstream")
    return "ok (" + "; ".join(msgs) + ")" if msgs else "ok (no remotes)"


def auto_commit(core, paths, message):
    """Commit only `paths` in the core as an automatic action: message prefixed `auto:` so the
    history of what kc did on its own is `git log --grep '^auto:'` (ADR 0005)."""
    if not is_repo(core):
        return False
    git(core, "add", "-A", "--", *paths)
    if not git(core, "diff", "--cached", "--quiet", "--", *paths).returncode:
        return False
    r = git(core, "commit", "-m", f"auto: {message}", "--", *paths)
    return r.returncode == 0


def push(path):
    if "origin" not in remotes(path):
        return "no origin"
    b = branch(path)
    if b != BRANCH:
        return f"skipped (on branch '{b}')"
    if not _includes_origin(path):
        return "not pushed: origin has commits you have not synced — run `kc pull-all` first"
    r = git(path, "push", "--force-with-lease", "-u", "origin", BRANCH)
    if r.returncode == 0:
        return "pushed"
    return f"fail: {last(r.stderr)} — someone pushed meanwhile; run `kc pull-all`, then push again"


def _includes_origin(path):
    """True if the local branch has, at some point, contained origin's tip — i.e. any rewrite
    of it was made on top of what origin had (our own --force-if-includes; git's version
    rejects fresh clones). Plus --force-with-lease, nobody else's push can be overwritten."""
    ref = f"refs/remotes/origin/{BRANCH}"
    if not has_ref(path, ref):
        return True
    tip = git(path, "rev-parse", ref).stdout.strip()
    if git(path, "merge-base", "--is-ancestor", tip, "HEAD").returncode == 0:
        return True
    return tip in git(path, "rev-list", "-g", BRANCH).stdout.split()
