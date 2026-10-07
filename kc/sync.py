"""Session boundaries: `kc sync`, `kc status`, `kc hook start|end` (ADR 0015).

- sync: commit leftovers, pull, push — the core and every module present on this device.
- signals: cheap, unambiguous facts that call for maintenance (format problems, a module that
  grew since its last structure review, a manual procedure repeated 3 times). kc only reports
  them; the agent raises them with the human.
"""
import datetime
import re
import subprocess
import sys
from . import core as C
from . import git as G
from .registry import count_notes


def _targets(core):
    """[(name, path, kind)] — kind: own | frozen | external. Modules not set up here are skipped."""
    out = [("core", core, "own")]
    for m in C.modules(core):
        if not m["path"]:
            continue
        kind = "external" if m["external"] else "frozen" if m["status"] == "frozen" else "own"
        out.append((m["name"], m["path"], kind))
    return out


def _print(title, rows):
    if not rows:
        return
    print(title)
    w = max(len(n) for n, _ in rows)
    for n, s in rows:
        print(f"  {n.ljust(w)}  {s}")


def sync_all(core, message=None):
    message = message or f"auto: sync from {C.device_id(core) or 'unknown device'}"
    rows, failed = [], False
    for name, path, kind in _targets(core):
        if kind == "external":
            status, bad = G.sync_external(path)
        else:
            status, bad = G.sync_own(path, message, frozen=(kind == "frozen"))
        rows.append((name, status))
        failed = failed or bad
    return rows, failed


# ---------------------------------------------------------------- signals
def _check_problems(m):
    try:
        cmd = re.sub(r"^python3? ", lambda _: f'"{sys.executable}" ', m["check"])  # same python as kc
        r = subprocess.run(cmd, shell=True, cwd=m["path"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        return f"check timed out: {m['check']}"
    if r.returncode != 0:
        return f"{G.last(r.stdout) or G.last(r.stderr)} — run `{m['check']}` in the module and fix"
    return None


def _review_due(m, inst, today):
    rev = m["reviewed"] or {}
    now = count_notes(m["path"])
    grown = now - int(rev.get("notes") or 0)
    if grown <= 0:
        return None
    limit_notes = int(inst.get("review_after_notes", 25))
    limit_days = int(inst.get("review_after_days", 60))
    since = rev.get("date")
    days = (today - datetime.date.fromisoformat(str(since))).days if since else None
    if grown >= limit_notes or (days is not None and days >= limit_days):
        when = f"since {since}" if since else "since it was added"
        return (f"+{grown} notes {when} — review its structure (split? a new module? a process?), "
                f"then `kc reviewed {m['name']}`")
    return None


REPEAT = re.compile(r"^-\s*(\d+)\s*[×x]\s*·\s*(.+)$")


def _todo(core):
    """Counts of open items per section of ecosystem/todo.md, and repeats that reached 3."""
    f = core / "ecosystem" / "todo.md"
    if not f.exists():
        return {}, []
    counts, repeats, section = {}, [], None
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if not section or not line.startswith("- "):
            continue
        if section == "repeats":
            m = REPEAT.match(line)
            if m and int(m.group(1)) >= 3:
                repeats.append(m.group(2).split("·")[0].strip())
        else:
            counts[section] = counts.get(section, 0) + 1
    return counts, repeats


def signals(core):
    inst = C.load_instance(core)
    today = datetime.date.today()
    rows = []
    for m in C.modules(core):
        if m["external"] or m["status"] == "frozen" or not (m["path"] and m["path"].exists()):
            continue
        if m["check"]:
            p = _check_problems(m)
            if p:
                rows.append((m["name"], f"format: {p}"))
        r = _review_due(m, inst, today)
        if r:
            rows.append((m["name"], f"structure: {r}"))
    counts, repeats = _todo(core)
    for r in repeats:
        rows.append(("todo", f"repeat: done 3+ times by hand — propose a process: {r}"))
    if counts:
        rows.append(("todo", "open: " + ", ".join(f"{n} {s}" for s, n in counts.items())
                             + " (ecosystem/todo.md)"))
    return rows


# ---------------------------------------------------------------- commands
def cmd_sync(core, message=None):
    rows, failed = sync_all(core, message)
    _print("sync:", rows)
    return 1 if failed else 0


def cmd_status(core):
    rows = []
    for name, path, kind in _targets(core):
        if not G.is_repo(path):
            rows.append((name, "absent"))
            continue
        bits = [kind] if kind != "own" else []
        if G.conflicted(path):
            bits.append("CONFLICT unresolved")
        if G.dirty(path):
            bits.append("uncommitted changes")
        ahead, behind = G.ahead_behind(path)
        if ahead:
            bits.append(f"{ahead} not pushed")
        if behind:
            bits.append(f"{behind} to pull")
        rows.append((name, ", ".join(bits) or "clean"))
    _print("repos (as of the last fetch):", rows)
    _print("signals:", signals(core))
    return 0


def hook(core, event):
    """Assistant hooks. Output of `start` goes into the session's context; `end` runs quietly.
    Always exit 0: a hook failure must not block the session — problems are in the report."""
    if event == "start":
        rows, _ = sync_all(core)
        _print("kc sync:", rows)
        sig = signals(core)
        _print("kc signals (raise these with the human — see AGENTS.md):", sig)
        if not sig:
            print("kc signals: none")
    elif event == "end":
        sync_all(core)
    else:
        print(f"kc hook: unknown event '{event}' (start | end)")
    return 0
