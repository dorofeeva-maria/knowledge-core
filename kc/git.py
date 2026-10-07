"""Git plumbing for the core and its modules (ADR 0015).

Every own repo has one branch, `main`, and one remote, `origin` (your repo, shared by your
devices). Sync never rewrites published history and never force-pushes:

    commit leftovers → fetch → rebase local commits onto origin/main → push

A conflict stops that repo only: the rebase is aborted, local commits stay, nothing is pushed.
Frozen repos are fast-forwarded only. External repos (not yours) are fast-forwarded on whatever
branch they are on, and only when clean; kc never commits or pushes them.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

BRANCH = "main"
NET_TIMEOUT = 60          # seconds for network git ops, so a hook never hangs
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


def first(s):
    """The most telling line of git's stderr (the first 'fatal:'/'error:' line, else the first)."""
    lines = [l.strip() for l in (s or "").strip().splitlines() if l.strip()]
    for l in lines:
        if l.startswith(("fatal:", "error:")):
            return l
    return lines[0] if lines else ""


def is_repo(path):
    return bool(path) and (Path(path) / ".git").exists()


def dirty(path):
    return bool(git(path, "status", "--porcelain").stdout.strip())


def has_origin(path):
    return "origin" in git(path, "remote").stdout.split()


def origin_url(path):
    r = git(path, "remote", "get-url", "origin")
    return r.stdout.strip() if r.returncode == 0 else ""


def branch(path):
    return git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def has_ref(path, ref):
    return git(path, "rev-parse", "--verify", "--quiet", ref).returncode == 0


def conflicted(path):
    """An unfinished rebase/merge or unmerged files."""
    gd = Path(path) / ".git"
    if (gd / "rebase-merge").exists() or (gd / "rebase-apply").exists() or (gd / "MERGE_HEAD").exists():
        return True
    return bool(git(path, "diff", "--name-only", "--diff-filter=U").stdout.split())


def ahead_behind(path):
    """(ahead, behind) of HEAD vs origin/main from the last fetch; (None, None) if unknown."""
    if not has_ref(path, f"refs/remotes/origin/{BRANCH}"):
        return None, None
    r = git(path, "rev-list", "--left-right", "--count", f"HEAD...origin/{BRANCH}")
    try:
        a, b = r.stdout.split()
        return int(a), int(b)
    except ValueError:
        return None, None


def _classify_push(stderr):
    s = (stderr or "").lower()
    if "protected branch" in s or "gh006" in s:
        return "rejected by branch protection"
    if "large files" in s or "exceeds github's file size limit" in s or "gh001" in s:
        return "a file is too large for the host — move it out or add it to the repo's .gitignore"
    if "permission" in s or "denied" in s or "authentication failed" in s or "403" in s:
        return "permission denied — check your access (`gh auth status`)"
    if "could not resolve" in s or "timed out" in s or "unable to access" in s:
        return "network error — will retry on the next sync"
    if "fetch first" in s or "non-fast-forward" in s or "rejected" in s:
        return "origin moved meanwhile — will retry on the next sync"
    return last(stderr) or "push failed"


def commit_all(path, message):
    """Stage everything and commit. Returns None if nothing to commit, else (ok, detail)."""
    git(path, "add", "-A")
    if git(path, "diff", "--cached", "--quiet").returncode == 0:
        return None
    r = git(path, "commit", "-q", "-m", message)
    return (r.returncode == 0, last(r.stderr) or last(r.stdout))


def sync_own(path, message, frozen=False):
    """Sync one of your repos. Returns (status line, failed?)."""
    if not is_repo(path):
        return "absent", False
    if conflicted(path):
        return f"CONFLICT unresolved — finish it: git -C \"{path}\" status", True
    notes = []
    if dirty(path):
        if frozen:
            return "frozen but has local changes — not committed; revert or unfreeze", True
        res = commit_all(path, message)
        if res and not res[0]:
            return f"commit failed: {res[1]}", True
        if res:
            notes.append("committed leftovers")
    if not has_origin(path):
        return ", ".join(notes + ["no remote — stays on this device"]), False
    b = branch(path)
    if b != BRANCH:
        return f"skipped (on branch '{b}', expected '{BRANCH}')", True
    fr = git(path, "fetch", "--quiet", "origin", timeout=NET_TIMEOUT)
    if fr.returncode != 0:
        return ", ".join(notes + [f"fetch failed ({first(fr.stderr) or 'offline?'}) — local commits kept"]), True
    ahead, behind = ahead_behind(path)
    if behind:
        if frozen or not ahead:
            r = git(path, "merge", "--ff-only", "--quiet", f"origin/{BRANCH}")
            if r.returncode != 0:
                return f"fast-forward failed: {last(r.stderr)}", True
            notes.append(f"pulled {behind}")
        else:
            r = git(path, "rebase", "--quiet", f"origin/{BRANCH}")
            if r.returncode != 0:
                files = git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
                git(path, "rebase", "--abort")
                return (f"CONFLICT with origin ({', '.join(files[:3]) or last(r.stderr)}) — not pushed; "
                        f"resolve: git -C \"{path}\" pull --rebase origin {BRANCH}"), True
            notes.append(f"pulled {behind}")
    ahead, _ = ahead_behind(path) if has_ref(path, f"refs/remotes/origin/{BRANCH}") else (1, 0)
    if ahead and not frozen:
        r = git(path, "push", "--quiet", "-u", "origin", BRANCH, timeout=NET_TIMEOUT)
        if r.returncode != 0:
            return ", ".join(notes + [f"NOT PUSHED: {_classify_push(r.stderr)}"]), True
        notes.append(f"pushed {ahead}")
    return ", ".join(notes) or "up to date", False


def sync_external(path):
    """Fast-forward a repo that is not yours; never commit or push it."""
    if not is_repo(path):
        return "absent", False
    if conflicted(path) or dirty(path):
        return "skipped (local changes — not ours to commit)", False
    before = git(path, "rev-parse", "HEAD").stdout.strip()
    r = git(path, "pull", "--ff-only", "--quiet", timeout=NET_TIMEOUT)
    if r.returncode != 0:
        return f"not updated: {first(r.stderr) or 'pull failed'}", False
    n = git(path, "rev-list", "--count", f"{before}..HEAD").stdout.strip() if before else ""
    return (f"pulled {n} (ff)" if n and n != "0" else "up to date (ff)"), False


# ---------------------------------------------------------------- privacy (ADR 0015)
def _is_local_remote(url):
    if "://" in url:
        return url.split("://", 1)[0] == "file"
    if re.match(r"^[^/\\]+@[^/:]+:", url):   # scp-like git@host:path
        return False
    return True


def visibility(url):
    """'local' | 'private' | 'public' | 'non-github' | 'unknown' (gh missing or not logged in)."""
    if not url:
        return "local"
    if _is_local_remote(url):
        return "local"
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return "non-github"
    if not shutil.which("gh"):
        return "unknown"
    r = subprocess.run(["gh", "repo", "view", f"{m.group(1)}/{m.group(2)}", "--json", "visibility",
                        "-q", ".visibility"], capture_output=True, text=True, env=_ENV)
    v = r.stdout.strip().lower() if r.returncode == 0 else ""
    return {"private": "private", "internal": "private", "public": "public"}.get(v, "unknown")


def private_problem(url):
    """Is `url` safe for private content? Checked once — when a private repo gets its remote —
    not on every push. Returns (None, None) if verified or local; ("stop", why) if it is a
    public repo; ("warn", why) if kc cannot verify it (not on GitHub, or gh missing)."""
    v = visibility(url)
    if v in ("local", "private"):
        return None, None
    if v == "public":
        return "stop", f"{url} is a PUBLIC repo — make it private or use another one"
    if v == "non-github":
        return "warn", f"{url} is not on GitHub, so kc cannot verify it is private — make sure it is"
    return "warn", f"cannot verify {url} is private (install GitHub CLI, `gh auth login`) — make sure it is"


def enforce_private(url, what):
    """Refuse a public remote for private content; warn when it cannot be verified."""
    level, why = private_problem(url)
    if level == "stop":
        raise SystemExit(f"{what}: not done — the content is private but {why}")
    if level == "warn":
        print(f"  WARNING: {why}")
