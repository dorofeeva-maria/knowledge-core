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
import re
import shutil
import subprocess
from pathlib import Path

BRANCH = "main"
NET_TIMEOUT = 60          # seconds for network git ops (fetch / pull / push), so they never hang
_ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}


def git(path, *args, timeout=None):
    try:
        return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=_ENV, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(list(args), 124, "", f"timed out after {timeout}s")


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


def conflicted(path):
    """An unfinished rebase/merge or unmerged files: committing now would record conflict markers
    as resolved and can drop a commit (finding A4)."""
    return _rebase_in_progress(path) or bool(_unmerged(path))


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
    fr = git(path, "fetch", "--all", "--prune", "--quiet", timeout=NET_TIMEOUT)
    if fr.returncode != 0:
        return f"sync skipped (fetch failed: {last(fr.stderr) or 'network?'})"
    msgs = []
    if "origin" in remotes(path) and has_ref(path, f"refs/remotes/origin/{BRANCH}"):
        ok, files = rebase(path, "rebase", f"origin/{BRANCH}")   # already fetched; separates network from conflict
        if not ok:
            git(path, "rebase", "--abort")
            return (f"CONFLICT with origin ({', '.join(files[:3])}) — resolve by hand: "
                    f"git -C {path} rebase origin/{BRANCH}")
        msgs.append("origin")
    prepare(path, upstream_url() if callable(upstream_url) else upstream_url)
    if "upstream" in remotes(path):
        ur = git(path, "fetch", "upstream", "--quiet", timeout=NET_TIMEOUT)
        if ur.returncode != 0:
            msgs.append(f"upstream fetch failed ({last(ur.stderr) or 'network?'})")
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


def large_limit(core=None):
    """Bytes above which a file is never committed (instance `large_file_mb`, default 20)."""
    mb = 20
    if core is not None:
        try:
            from .core import load_instance
            mb = float(load_instance(core).get("large_file_mb", 20))
        except Exception:
            pass
    return int(mb * 1024 * 1024)


def stage(path, paths=None, limit=None):
    """`git add` (all, or `paths`), then unstage files larger than the limit. Returns the
    list of files left out, so callers can tell the human (ADR 0007)."""
    git(path, "add", "-A", *(["--", *paths] if paths else []))
    limit = limit or large_limit()
    big = []
    for f in git(path, "diff", "--cached", "--name-only", "--diff-filter=AM").stdout.splitlines():
        fp = Path(path) / f
        if fp.exists() and fp.stat().st_size > limit:
            git(path, "reset", "-q", "--", f)
            big.append(f)
    return big


def auto_commit(core, paths, message, and_push=True):
    """Commit only `paths` in the core as an automatic action: message prefixed `auto:` so the
    history of what kc did on its own is `git log --grep '^auto:'` (ADR 0005). Pushed right
    away, like every commit to the core (ADR 0006)."""
    if not is_repo(core):
        return False
    if conflicted(core):
        print("  not committed — the core has an unfinished rebase/conflict; resolve it first "
              "(`kc update core`)")
        return False
    big = stage(core, paths, large_limit(core))
    if big:
        print(f"  not committed (over {large_limit(core) // 2**20} MB, stays on this device): "
              + ", ".join(big))
    if not git(core, "diff", "--cached", "--quiet", "--", *paths).returncode:
        return False
    r = git(core, "commit", "-m", f"auto: {message}", "--", *paths)
    if r.returncode == 0 and and_push:
        print("  " + push(core, private_required=True))   # the core is always private (ADR 0014)
    return r.returncode == 0


def _same_url(a, b):
    def norm(u):
        u = str(u or "")
        if u and Path(u).exists():            # local path remotes: compare resolved paths
            u = str(Path(u).resolve())
        return u.rstrip("/").removesuffix(".git").replace("\\", "/").lower()
    return norm(a) == norm(b)


def contract(path, remote=None, upstream_url=None):
    """What the core expects of its own (non-external) repos (ADR 0008): branch `main`, no
    rebase stuck, `origin` = registry remote, `upstream` = registry upstream."""
    if not is_repo(path):
        return []
    out = []
    b = branch(path)
    if b != BRANCH:
        out.append(f"on branch '{b}', expected '{BRANCH}'")
    if _rebase_in_progress(path):
        out.append("rebase in progress")
    rs = remotes(path)
    if remote:
        url = git(path, "remote", "get-url", "origin").stdout.strip() if "origin" in rs else ""
        if not _same_url(url, remote):
            out.append(f"origin is '{url or 'missing'}', registry says '{remote}'")
    if isinstance(upstream_url, str) and upstream_url:
        url = git(path, "remote", "get-url", "upstream").stdout.strip() if "upstream" in rs else ""
        if not _same_url(url, upstream_url):
            out.append(f"upstream is '{url or 'missing'}', registry says '{upstream_url}'")
    return out


def _origin_url(path):
    r = git(path, "remote", "get-url", "origin")
    return r.stdout.strip() if r.returncode == 0 else ""


def _is_local_remote(url):
    if "://" in url:
        return url.split("://", 1)[0] == "file"
    if re.match(r"^[^/\\]+@[^/:]+:", url):   # scp-like git@host:path → remote
        return False
    return True                              # bare filesystem path


def _github_owner_repo(url):
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def _gh_visibility(owner_repo):
    """'private' | 'public' | None (gh missing / not authed / error)."""
    if not shutil.which("gh"):
        return None
    r = subprocess.run(["gh", "repo", "view", owner_repo, "--json", "visibility", "-q", ".visibility"],
                       capture_output=True, text=True, env=_ENV)
    if r.returncode != 0:
        return None
    v = r.stdout.strip().lower()
    return "private" if v in ("private", "internal") else "public" if v == "public" else None


def origin_privacy(path):
    """How safe `origin` is for private content (ADR 0014):
    'local' | 'private' | 'public' | 'unknown-github' | 'non-github' | 'none'."""
    url = _origin_url(path)
    if not url:
        return "none"
    if _is_local_remote(url):
        return "local"
    owner_repo = _github_owner_repo(url)
    if owner_repo is None:
        return "non-github"
    return _gh_visibility(owner_repo) or "unknown-github"


def _classify_push(stderr):
    s = (stderr or "").lower()
    if "protected branch" in s or ("protected" in s and "reject" in s):
        return "rejected by branch protection — open a PR instead"
    if "permission" in s or "denied" in s or "authentication failed" in s or "403" in s:
        return "permission denied — check your access (`gh auth status`)"
    if ("could not resolve" in s or "timed out" in s or "timeout" in s
            or "unable to access" in s or "network" in s):
        return "network error — check your connection, then retry"
    if ("stale info" in s or "fetch first" in s or "non-fast-forward" in s or "behind" in s
            or "[rejected]" in s or "rejected" in s or "failed to push" in s):
        return "someone pushed meanwhile; run `kc pull-all`, then push again"
    return last(stderr) or "push failed"


def push(path, private_required=False):
    if "origin" not in remotes(path):
        return "no origin"
    b = branch(path)
    if b != BRANCH:
        return f"skipped (on branch '{b}')"
    if private_required:
        vis = origin_privacy(path)
        if vis == "public":
            return ("NOT PUSHED — private content, but origin is a PUBLIC GitHub repo. Make the "
                    "repo private, or point origin at a private one.")
        if vis == "unknown-github":
            return ("NOT PUSHED — cannot verify origin is private. Install GitHub CLI and run "
                    "`gh auth login`, then retry (private content is never pushed unverified).")
        if vis == "non-github":
            return ("NOT PUSHED — private content headed to a non-GitHub remote. It goes only to a "
                    "private GitHub repo (a work GitLab is NOT private). Ask the human what this is.")
        if vis == "none":
            return "no origin"
        # 'local' or 'private' → safe
    if not _includes_origin(path):
        return "not pushed: origin has commits you have not synced — run `kc pull-all` first"
    r = git(path, "push", "--force-with-lease", "-u", "origin", BRANCH, timeout=NET_TIMEOUT)
    return "pushed" if r.returncode == 0 else f"fail: {_classify_push(r.stderr)}"


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
