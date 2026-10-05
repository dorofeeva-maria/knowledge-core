"""Cross-repo mechanical ops: registry view, pull-all, commit-push, check-drafts.

Deterministic plumbing the `close` skill (and the session-start hook) call. Pushing is
opt-in (`--push`) so nothing leaves the machine without an explicit decision.
"""
import subprocess
from pathlib import Path
from . import center as C


def _git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)


def _last(s):
    lines = (s or "").strip().splitlines()
    return lines[-1] if lines else ""


def _is_repo(path):
    return bool(path) and (Path(path) / ".git").exists()


def _dirty(path):
    return bool(_git(path, "status", "--porcelain").stdout.strip())


def _has_remote(path, name):
    return name in _git(path, "remote").stdout.split()


def _repo_root(path):
    r = _git(path, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def _print_report(report):
    w = max((len(n) for n, _ in report), default=4)
    for n, s in report:
        print(f"  {n.ljust(w)}  {s}")


# ---------------------------------------------------------------- registry
def show_registry(center):
    mods, did = C.resolve(center)
    print(f"center: {center}")
    print(f"device: {did or '(KC_DEVICE_ID unset)'}")
    if not mods:
        print("modules: none in registry")
        return
    w = max(len(m["name"]) for m in mods)
    for m in mods:
        here = "here" if (m["path"] and m["path"].exists()) else ("absent" if m["path"] else "no-path")
        flags = [m["status"]] + (["external"] if m["external"] else []) + (["private"] if m["private"] else [])
        print(f"  {m['name'].ljust(w)}  {here:7}  {' '.join(flags)}")


# ---------------------------------------------------------------- pull
def pull_one(path, external):
    if not _is_repo(path):
        return "absent"
    if _dirty(path):
        return "skipped (dirty)"
    if external:  # their branches / upstream are not ours to touch
        r = _git(path, "pull", "--ff-only")
        return "ok (ff)" if r.returncode == 0 else f"fail: {_last(r.stderr)}"
    msgs = []
    if _has_remote(path, "upstream"):
        r = _git(path, "pull", "upstream", "main", "--rebase")
        if r.returncode != 0:
            return f"fail (upstream rebase): {_last(r.stderr)}"
        msgs.append("upstream rebased")
    if _has_remote(path, "origin"):
        r = _git(path, "pull", "--ff-only")
        if r.returncode != 0:
            return f"fail (origin ff): {_last(r.stderr)}"
        msgs.append("origin ff")
    return "ok (" + ", ".join(msgs) + ")" if msgs else "ok (no remotes)"


def pull_all(center):
    report = [("center", pull_one(center, False))]
    mods, _ = C.resolve(center)
    for m in mods:
        if m["status"] == "disconnected":
            continue
        report.append((m["name"], pull_one(m["path"], m["external"])))
    _print_report(report)
    return report


# ---------------------------------------------------------------- commit / push
def commit_push(center, message, all_repos=False, do_push=False):
    targets = []
    if all_repos:
        targets.append(("center", center))
        for m in C.resolve(center)[0]:
            if m["external"] or m["status"] in ("disconnected", "frozen"):
                continue
            if m["path"]:
                targets.append((m["name"], m["path"]))
    else:
        root = _repo_root(Path.cwd())
        if not root:
            raise SystemExit("kc commit-push: not inside a git repo")
        targets.append((root.name, root))
    report = []
    for name, path in targets:
        if not _is_repo(path):
            report.append((name, "absent"))
            continue
        if not _dirty(path):
            report.append((name, "nothing to commit"))
            continue
        _git(path, "add", "-A")
        r = _git(path, "commit", "-m", message)
        if r.returncode != 0:
            report.append((name, f"commit fail: {_last(r.stderr)}"))
            continue
        if do_push and _has_remote(path, "origin"):
            rp = _git(path, "push")
            report.append((name, "committed+pushed" if rp.returncode == 0 else f"committed, push fail: {_last(rp.stderr)}"))
        else:
            report.append((name, "committed" + ("" if do_push else " (no push)")))
    _print_report(report)
    return report


def push_all(center):
    targets = [("center", center)]
    for m in C.resolve(center)[0]:
        if m["external"] or m["status"] in ("disconnected", "frozen"):
            continue
        if m["path"]:
            targets.append((m["name"], m["path"]))
    report = []
    for name, path in targets:
        if not _is_repo(path):
            report.append((name, "absent"))
        elif not _has_remote(path, "origin"):
            report.append((name, "no origin"))
        else:
            r = _git(path, "push")
            report.append((name, "pushed" if r.returncode == 0 else f"fail: {_last(r.stderr)}"))
    _print_report(report)
    return report


# ---------------------------------------------------------------- drafts / inbox
def check_drafts(center):
    def items(name):
        d = center / name
        if not d.exists():
            return []
        return [f.name for f in d.iterdir() if f.name != "README.md" and not f.name.startswith(".")]

    inbox, drafts = items("inbox"), items("drafts")
    if not inbox and not drafts:
        print("inbox/drafts: empty")
        return 0
    if inbox:
        print(f"inbox:  {len(inbox)} item(s) — {', '.join(inbox[:5])}{'…' if len(inbox) > 5 else ''}")
    if drafts:
        print(f"drafts: {len(drafts)} item(s) — {', '.join(drafts[:5])}{'…' if len(drafts) > 5 else ''}")
    print("→ run `close` to process before new work")
    return 1
