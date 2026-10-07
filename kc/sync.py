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
    """[(name, path, kind, module)] — kind: own | frozen | external. Not set up here: skipped."""
    out = []
    for m in C.modules(core):
        if not m["path"]:
            continue
        kind = "external" if m["external"] else "frozen" if m["status"] == "frozen" else "own"
        out.append((m["name"], m["path"], kind, m))
    return out


def _print(title, rows):
    if not rows:
        return
    print(title)
    w = max(len(n) for n, _ in rows)
    for n, s in rows:
        print(f"  {n.ljust(w)}  {s}")


def sync_all(core, message=None, seconds=None):
    """Sync the core first (plain git, so a bad registry can be fixed by a pull), then every
    module present on this device. `seconds` caps the network time of the whole run."""
    import time
    message = message or f"auto: sync from {C.device_id(core) or 'unknown device'}"
    end = time.monotonic() + seconds if seconds else None
    budget = (lambda: end - time.monotonic()) if end else None
    rows, failed = [], False

    def add(name, status, bad):
        nonlocal failed
        rows.append((name, ("FAIL: " + status) if bad else status))
        failed = failed or bad

    add("core", *G.sync_own(core, message, budget=budget))
    try:
        targets = _targets(core)
    except SystemExit as e:              # the registry is unreadable: report, sync nothing else
        add("registry", str(e), True)
        return rows, True
    for name, path, kind, m in targets:
        if kind == "external":
            add(name, *G.sync_external(path))
        else:
            add(name, *G.sync_own(path, message, frozen=(kind == "frozen"), remote=m["remote"],
                                  private=m["private"], budget=budget))
    for problem in C.registry_problems(core):
        add("registry", problem, True)
    try:
        C.grant_module_dirs(core)
    except SystemExit as e:              # a broken settings file must not stop the sync
        add("claude", str(e), True)
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
    try:
        days = (today - datetime.date.fromisoformat(str(since))).days if since else None
    except ValueError:
        days = None
    if grown >= limit_notes or (days is not None and days >= limit_days):
        when = f"since {since}" if since else "since it was added"
        return (f"+{grown} notes {when} — review its structure (split? a new module? a process?), "
                f"then `kc reviewed {m['name']}`")
    return None


REPEAT = re.compile(r"^[-*]\s*(?:\[[ ]\]\s*)?\**\s*(\d+)\s*(?:[×xх]|times|раз[а]?)\**\s*[·:\-—]?\s*(.+)$", re.I)
SECTIONS = {"tasks": "tasks", "задачи": "tasks", "candidates": "candidates", "кандидаты": "candidates",
            "repeats": "repeats", "повторы": "repeats"}


def _todo(core):
    """Open items per section of ecosystem/todo.md, and repeats that reached 3. HTML comments,
    code fences and checked items ([x]) are ignored; repeat lines may be written loosely."""
    f = core / "ecosystem" / "todo.md"
    if not f.exists():
        return {}, []
    text = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
    text = re.sub(r"^(```|~~~).*?^", "", text, flags=re.S | re.M)
    counts, repeats, section = {}, [], None
    for line in text.splitlines():
        if line.startswith("## "):
            section = SECTIONS.get(line[3:].strip().lower(), line[3:].strip().lower())
            continue
        s = line.strip()
        if not section or not s.startswith(("- ", "* ")) or re.match(r"^[-*]\s*\[[xX]\]", s):
            continue
        if section == "repeats":
            m = REPEAT.match(s)
            if m and int(m.group(1)) >= 3:
                what = re.split(r"\s+·\s+", m.group(2))[0].strip(" *")
                if what not in repeats:
                    repeats.append(what)
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
    for name, path, kind in [("core", core, "own")] + [t[:3] for t in _targets(core)]:
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
    try:
        if event == "start":
            rows, _ = sync_all(core, seconds=90)
            _print("kc sync (raise every FAIL line with the human):", rows)
            missing = [m["name"] for m in C.modules(core) if not m["path"]]
            if missing:
                print("kc: in the registry but not set up on this device: " + ", ".join(missing)
                      + " (set up: python -m kc bootstrap)")
            sig = signals(core)
            _print("kc signals (raise these with the human — see AGENTS.md):", sig)
            if not sig:
                print("kc signals: none")
            return 0
        if event == "end":
            sync_all(core, seconds=50)
            return 0
    except SystemExit as e:
        print(f"kc hook {event}: {e} — nothing else was synced; fix this first")
        return 0
    else:
        print(f"kc hook: unknown event '{event}' (start | end)")
    return 0
