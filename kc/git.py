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
_ENV = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
        "GIT_SSH_COMMAND": os.environ.get("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")}


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
    if "gh013" in s or "secret" in s:
        return ("rejected: the host found a secret in the commits — remove it from the unpushed "
                "commit (`git reset --soft origin/main`, fix, commit again)")
    if "large files" in s or ("exceeds" in s and "size" in s) or "gh001" in s:
        return ("rejected: a file is too large for the host — remove it from the unpushed commit "
                "(`git reset --soft origin/main`, `git rm --cached <file>`, add it to .gitignore, commit)")
    if "pre-receive" in s or "declined" in s:
        return f"rejected by the host: {first(stderr)}"
    if "permission" in s or "denied" in s or "authentication failed" in s or "403" in s:
        return "permission denied — check your access (`gh auth status`)"
    if "could not resolve" in s or "timed out" in s or "unable to access" in s:
        return "network error — will retry on the next sync"
    if "fetch first" in s or "non-fast-forward" in s:
        return "origin moved meanwhile — will retry on the next sync"
    return first(stderr) or "push failed"


LARGE = 50 * 2**20       # files above this are never committed by kc (hosts reject ~100 MB)


def commit_all(path, message):
    """Stage everything except files over LARGE and commit. Returns (result, left_out):
    result None = nothing to commit, else (ok, detail)."""
    git(path, "add", "-A")
    big = []
    for f in git(path, "diff", "--cached", "--name-only", "--diff-filter=AM", "-z").stdout.split("\0"):
        fp = Path(path) / f
        if f and fp.is_file() and fp.stat().st_size > LARGE:
            git(path, "reset", "-q", "--", f)
            big.append(f)
    if git(path, "diff", "--cached", "--quiet").returncode == 0:
        return None, big
    r = git(path, "commit", "-q", "-m", message)
    return (r.returncode == 0, first(r.stderr) or last(r.stdout)), big


def current_branch(path):
    """The checked-out branch, or None on a detached HEAD."""
    r = git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else None


def same_url(a, b):
    def norm(u):
        u = str(u or "").strip()
        if u and _is_local_remote(u) and "://" not in u:
            try:
                u = str(Path(u).resolve())     # short/long Windows names, relative paths
            except OSError:
                pass
        u = u.replace("\\", "/").rstrip("/")
        return (u[:-4] if u.endswith(".git") else u).lower()
    return norm(a) == norm(b)


PRIVATE_TAG = re.compile(r"^tags:.*\bprivate\b", re.M)


def _private_notes(path, since):
    """Markdown files touched by the commits about to be pushed (all files on a first push)
    whose frontmatter tags them `private`."""
    if since:
        files = git(path, "log", "--name-only", "--format=", f"{since}..HEAD").stdout.splitlines()
    else:
        files = git(path, "ls-files").stdout.splitlines()
    out = []
    for f in sorted({f for f in files if f.endswith(".md")}):
        fp = Path(path) / f
        if fp.is_file():
            head = fp.read_text(encoding="utf-8", errors="replace")[:3000]
            if head.startswith("---") and PRIVATE_TAG.search(head.split("\n---", 1)[0]):
                out.append(f)
    return out


def sync_own(path, message, frozen=False, remote=None, private=True, budget=None):
    """Sync one of your repos. `remote`: the registry's URL (origin must match it); `private`:
    the module's flag; `budget`: a function giving the seconds left for network work.
    Returns (status line, failed?)."""
    if not is_repo(path):
        return "absent", False
    if conflicted(path):
        return f"CONFLICT unresolved — finish it: git -C \"{path}\" status", True
    b = current_branch(path)
    if b != BRANCH:
        where = f"branch '{b}'" if b else "a detached HEAD"
        return f"skipped: on {where}, expected '{BRANCH}' — nothing committed", True
    notes = []
    if dirty(path):
        if frozen:
            return "frozen but has local changes — not committed; revert or unfreeze", True
        res, big = commit_all(path, message)
        if big:
            notes.append(f"left out (over {LARGE // 2**20} MB): {', '.join(big)} — add to .gitignore")
        if res and not res[0]:
            return ", ".join(notes + [f"commit failed: {res[1]}"]), True
        if res:
            notes.append("committed leftovers")
    if not has_origin(path):
        return ", ".join(notes + ["no remote — stays on this device"]), False
    if remote and not same_url(origin_url(path), remote):
        return ", ".join(notes + [f"NOT SYNCED: origin is {origin_url(path)} but the registry says "
                                  f"{remote} — change it with `kc set NAME remote=…`"]), True
    if budget is not None and budget() < 5:
        return ", ".join(notes + ["not synced: out of time — run `kc sync`"]), True
    t = NET_TIMEOUT if budget is None else max(5, min(NET_TIMEOUT, int(budget())))
    fr = git(path, "fetch", "--quiet", "origin", timeout=t)
    if fr.returncode != 0:
        return ", ".join(notes + [f"fetch failed ({first(fr.stderr) or 'offline?'}) — local commits kept"]), True
    has_main = has_ref(path, f"refs/remotes/origin/{BRANCH}")
    if not has_main and git(path, "branch", "-r").stdout.strip():
        return ", ".join(notes + [f"NOT SYNCED: origin has branches but no '{BRANCH}' — check the remote"]), True
    ahead, behind = ahead_behind(path)
    if behind:
        if frozen or not ahead:
            r = git(path, "merge", "--ff-only", "--quiet", f"origin/{BRANCH}")
            if r.returncode != 0:
                return ", ".join(notes + [f"fast-forward failed: {first(r.stderr)}"]), True
            notes.append(f"pulled {behind}")
        else:
            r = git(path, "rebase", "--quiet", f"origin/{BRANCH}")
            if r.returncode != 0:
                files = git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
                git(path, "rebase", "--abort")
                what = (f"CONFLICT with origin ({', '.join(files[:3])})" if files
                        else f"rebase onto origin failed ({first(r.stderr)})")
                return ", ".join(notes + [f"{what} — not pushed, local commits kept; resolve: "
                                          f"git -C \"{path}\" pull --rebase origin {BRANCH}"]), True
            notes.append(f"pulled {behind}")
    ahead = ahead_behind(path)[0] if has_main else 1
    if ahead and not frozen:
        if not private:
            leaked = _private_notes(path, f"origin/{BRANCH}" if has_main else None)
            if leaked:
                return ", ".join(notes + [f"NOT PUSHED: private-tagged notes in a non-private module "
                                          f"({', '.join(leaked[:3])}) — move them to a private module "
                                          f"or mark this one private (`kc set NAME private=true`)"]), True
        t = NET_TIMEOUT if budget is None else max(5, min(NET_TIMEOUT, int(budget())))
        r = git(path, "push", "--quiet", "-u", "origin", BRANCH, timeout=t)
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
    """A local path or file:// URL. Anything else — https://, ssh://, git@host:path, or an SSH
    host alias like `github-personal:me/x.git` — is a remote host."""
    if "://" in url:
        return url.split("://", 1)[0].lower() == "file"
    if re.match(r"^[A-Za-z]:[\\/]", url) or url.startswith(("/", "./", "../", "~")):
        return True
    if re.match(r"^[^/\\:]+:", url):        # host:path, with or without user@
        return False
    return Path(url).exists()


def visibility(url):
    """'local' | 'private' | 'public' | 'non-github' | 'unknown' (gh missing or not logged in)."""
    if not url:
        return "local"
    if _is_local_remote(url):
        return "local"
    m = re.search(r"github\.com(?::\d+)?[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url, re.I)
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
