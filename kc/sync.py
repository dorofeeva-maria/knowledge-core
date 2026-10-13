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

    def registry_ok():                   # checked after the pull, before the push: never push a
        try:                             # registry kc cannot read (it would stop every device
            C.load_registry(core)        # that pulls it) — a clean rebase can still merge one
            return None
        except SystemExit as e:
            return f"ecosystem/registry.yml is invalid — fix it, commit, then `kc sync` ({e})"

    add("core", *G.sync_own(core, message, budget=budget, validate=registry_ok))
    try:
        targets = _targets(core)
    except SystemExit as e:              # the registry is unreadable: report, sync nothing else
        add("registry", str(e), True)
        return rows, True
    for name, path, kind, m in targets:
        if kind == "external":
            add(name, *G.sync_external(path, budget=budget))
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


PLACEHOLDER = re.compile(r"^> Replace |Replace on first use", re.M)


def _placeholders(path):
    for fn in ("AGENTS.md", "README.md"):
        f = path / fn
        if f.exists() and PLACEHOLDER.search(f.read_text(encoding="utf-8", errors="replace")):
            return True
    return False


REPEAT = re.compile(r"^[-*]\s*(?:\[[ ]\]\s*)?\**\s*(\d+)\s*(?:[×xх]|times|раз[а]?)(?=[\s*·:\-—])\**\s*[·:\-—]?\s*(.+)$", re.I)
SECTIONS = {"tasks": "tasks", "задачи": "tasks", "candidates": "candidates", "кандидаты": "candidates",
            "repeats": "repeats", "повторы": "repeats",
            "обсудить": "discuss", "discuss": "discuss", "сроки": "dated", "deadlines": "dated", "dated": "dated",
            "техническое": "tech", "technical": "tech", "tech": "tech"}
ITEM_SECTIONS = ("discuss", "dated", "tech")    # items surfaced one by one, by their fields
FIELD = re.compile(r"^(due|after|when|module|device|confirm|postponed):\s*(\S.*)$", re.I)
RU_FIELD = re.compile(r"^(срок|до|после|когда|модуль|устройство)\s*:", re.I)   # a field typed in Russian
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")         # YYYY-MM-DD only, the same on every Python
DATE_KEYS = ("due", "after", "when")
DEVICES = ("mac", "windows", "linux")
SOON_DAYS = 3                                    # a `due` this close is surfaced
POSTPONE_WARN = 5                                # "the next session" this many times → warn
SHORT = 110


def _section(heading):
    """`## Dated:` / `##📅 Сроки (deadlines)` → "dated"; an unknown heading keeps its own name.
    Section names are recognised in English and Russian."""
    words = re.findall(r"[^\W\d_]+", heading.lower())
    for w in words:
        if w in SECTIONS:
            return SECTIONS[w]
    return heading.strip().lower()


def _item(s):
    """`- key: v · key: v · text` → ({key: v}, text, [problems]). Fields come first; the first
    segment that is not a known `key: value` starts the text (which may itself contain ` · `)."""
    parts = re.split(r"\s*·\s*", re.sub(r"^(?:[-*+]|\d+[.)])\s*(?:\[ \]\s*)?", "", s).strip())
    fields, problems = {}, []
    while parts:
        m = FIELD.match(parts[0].strip())
        if not m:
            break
        k = m.group(1).lower()
        if k in fields:
            problems.append(f"{k} twice")
        fields[k] = m.group(2).strip()
        parts.pop(0)
    if parts and RU_FIELD.match(parts[0].strip()):
        problems.append(f"field in Russian ({parts[0].split(':')[0].strip()}) — use due/after/when")
    return fields, " · ".join(p for p in parts if p).strip(), problems


def _device():
    return {"darwin": "mac", "win32": "windows", "cygwin": "windows", "msys": "windows"}.get(
        sys.platform, "linux" if sys.platform.startswith("linux") else sys.platform)


def _today(core):
    """(today, problem): today in the instance's time zone (`timezone:` in instance.yml); if that
    can't be used, the machine's date and a line saying why. Never raises: a broken instance.yml
    must not stop the sync."""
    try:
        tz = (C.load_instance(core) or {}).get("timezone")
    except (Exception, SystemExit) as e:
        return datetime.date.today(), f"ecosystem/instance.yml unreadable ({e}) — using the machine's date"
    if not tz:
        return datetime.date.today(), "no `timezone` in ecosystem/instance.yml — using the machine's date"
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(str(tz))).date(), None
    except Exception:
        return datetime.date.today(), (f"time zone {tz!r} not available — using the machine's date "
                                       "(on Windows: python -m pip install tzdata)")


def _dates(fields):
    """{key: date} for due/after/when, and the first malformed one as `key: value` (or None)."""
    out, bad = {}, None
    for k in DATE_KEYS:
        if k in fields:
            try:
                if not ISO.match(fields[k]):
                    raise ValueError
                out[k] = datetime.date.fromisoformat(fields[k])
            except ValueError:
                bad = bad or f"{k}: {fields[k]}"
    return out, bad


def _due_label(due, today):
    n = (due - today).days
    left = (f"overdue {-n} day{'s' * (n != -1)}" if n < 0 else "today" if n == 0
            else f"in {n} day{'s' * (n != 1)}")
    return f"due {due} ({left})"


def _surface(section, fields, problems, today, device):
    """(label, kind) to show an item under at session start; kind None = silent today,
    "device" = silent here because it belongs to the other device."""
    dev = fields.get("device", "").lower()
    if dev and dev not in DEVICES:
        return f"bad device ({fields['device']}) — use mac, windows or linux", "show"
    if problems:
        return f"fix the line: {', '.join(problems)}", "show"
    if dev and dev != device:
        return None, "device"
    d, bad = _dates(fields)
    if bad:
        return f"bad date ({bad}) — use YYYY-MM-DD", "show"
    when, after, due = d.get("when"), d.get("after"), d.get("due")
    if due and after and after > due:
        return f"after {after} is later than due {due} — fix the line", "show"
    if due and when and when > due:
        return f"agreed {when}, after its due {due} — move it", "show"
    if when and after and when < after:
        return f"agreed {when}, before its after {after} — move it", "show"
    soon = due and (due - today).days <= SOON_DAYS
    tail = f", {_due_label(due, today)}" if due else ""
    try:
        n = int(fields.get("postponed", 0))
    except ValueError:
        return f"fix the line: postponed: {fields['postponed']}", "show"
    if n >= POSTPONE_WARN:
        tail += f", postponed {n} times — offer a date or cancel"
    if when:                                     # an agreed day decides, in any section
        if when > today:
            return None, None
        if when == today:
            return f"today{tail}", "today"       # planned for today: a reminder, not a question
        return f"missed (when {when}){tail}", "show"
    if after and after > today:                  # not before `after`, even with a close due
        return None, None
    if section == "tech":
        name = f"tech ({dev})" if dev else "tech"
        if fields.get("confirm", "").lower() in ("yes", "да"):
            return f"{name}, needs consent{tail}", "show"
        return f"{name}{tail}", "tech"
    if soon:
        return _due_label(due, today), "show"
    if section == "discuss":
        return f"discuss{tail}", "show"
    if after:
        return f"after {after} reached{tail}", "show"
    if due:
        return None, None
    return "dated, but no date — add due/after/when", "show"


def _todo(core):
    """ecosystem/todo.md → (counts of plain sections, repeats that reached 3, items of the
    Discuss/Dated/Tech sections as (section, fields, text, problems)). HTML comments,
    code fences and checked items ([x]) are ignored; repeat lines may be written loosely."""
    f = core / "ecosystem" / "todo.md"
    if not f.exists():
        return {}, [], []
    raw = f.read_text(encoding="utf-8-sig", errors="replace")
    counts, repeats, items, section = {}, [], [], None
    if re.search(r"^(<{7}|={7}|>{7})( |$)", raw, re.M):
        raise ValueError("conflict markers in ecosystem/todo.md — resolve the conflict first "
                         "(AGENTS.md, Todo), then ask")
    fence, comment, opened = None, False, 0
    for no, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if comment:                              # inside <!-- … -->, only at line starts
            if "-->" in s:
                comment = False
            continue
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        m = re.match(r"^(```|~~~)", s)
        if m:
            fence, opened = m.group(1), no
            continue
        if s.startswith("<!--"):
            comment, opened = "-->" not in s[4:], no
            continue
        if re.match(r"^##(?!#)", s):
            section = _section(s[2:])
            continue
        if not section or not re.match(r"^(?:[-*+]|\d+[.)])\s", s) or re.match(r"^[-*+]\s*\[[xX]\]", s):
            continue
        if section == "repeats":
            m = REPEAT.match(s)
            if m and int(m.group(1)) >= 3:
                what = re.split(r"\s+·\s+", m.group(2))[0].strip(" *")
                if what not in repeats:
                    repeats.append(what)
        elif section in ITEM_SECTIONS:
            items.append((section, *_item(s)))
        else:
            counts[section] = counts.get(section, 0) + 1
    if fence or comment:
        what = "code fence" if fence else "<!-- comment"
        items.append(("discuss", {}, f"ecosystem/todo.md: unclosed {what} from line {opened} hides "
                                     "the lines below it — close it", ["fix the file"]))
    return counts, repeats, items


def _short(text):
    if not text:
        return "(no text)"
    return text if len(text) <= SHORT else text[:SHORT - 1].rstrip() + "…"


def _todo_rows(items, today, device):
    """One row per item to raise today, the ACTION rows, and the counts of silent ones."""
    rows, later, other, ask, tech, today_ = [], 0, 0, False, False, False
    for section, fields, text, problems in items:
        label, kind = _surface(section, fields, problems, today, device)
        if label is None:
            if kind == "device":
                other += 1
            else:
                later += 1
            continue
        mod = f" [{fields['module']}]" if fields.get("module") else ""
        rows.append(("todo", f"{label}{mod}: {_short(text)}"))
        if kind == "tech":
            tech = True
        elif kind == "today":
            today_ = True
        else:
            ask = True
    if ask:
        rows.append(("todo", "ACTION: ask the human about each item above that is not `today` "
                             "or plain `tech`, with AskUserQuestion, before their request "
                             "(see AGENTS.md, Todo)"))
    if today_:
        rows.append(("todo", "ACTION: `today` items are planned for today — remind the human, "
                             "don't ask"))
    if tech:
        rows.append(("todo", "ACTION: tech items — do them yourself when the session has room, "
                             "and report (see AGENTS.md, Todo)"))
    if later:
        rows.append(("todo", f"{later} more scheduled later (ecosystem/todo.md)"))
    if other:
        rows.append(("todo", f"{other} for the other device (ecosystem/todo.md)"))
    if device not in DEVICES and (other or any(f.get("device") for _, f, _, _ in items)):
        rows.append(("todo", f"this device reports itself as {device!r} — `device:` items can't "
                             "match it here"))
    return rows


def signals(core, today=None, core_failed=False):
    try:
        inst = C.load_instance(core)
    except (Exception, SystemExit) as e:         # say so, but keep the other signals
        inst = {}
        print(f"kc: ecosystem/instance.yml unreadable ({e})")
    tz_problem = None
    if today is None:
        today, tz_problem = _today(core)
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
        if _placeholders(m["path"]):
            rows.append((m["name"], "setup: template placeholders left in AGENTS.md/README.md — "
                                    "ask what the module is for and rewrite them"))
    if tz_problem:
        rows.append(("todo", tz_problem))
    if core_failed:                              # answers would go into an unsynced todo.md
        rows.append(("todo", "FAIL: the core did not sync — resolve its FAIL line first, then "
                             "ask about todo (run `kc status` to see the items)"))
        return rows
    try:
        counts, repeats, items = _todo(core)
    except Exception as e:                       # a broken todo.md must not hide other signals
        rows.append(("todo", f"FAIL: {e}" if isinstance(e, ValueError) else
                             f"FAIL: ecosystem/todo.md unreadable ({e})"))
        return rows
    for r in repeats:
        rows.append(("todo", f"repeat: done 3+ times by hand — propose a process: {r}"))
    rows += _todo_rows(items, today, _device())
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
            import time
            end = time.monotonic() + 105         # the hook's own limit is 120 s: network work
            today, tz_problem = _today(core)     # the day the session started, before the sync
            rows, _ = sync_all(core, seconds=85) # (offline: timeouts) shares what is left of it
            core_failed = any(n == "core" and v.startswith("FAIL") for n, v in rows)
            _print("kc sync (raise every FAIL line with the human):", rows)
            missing = [m["name"] for m in C.modules(core) if not m["path"]]
            if missing:
                print("kc: in the registry but not set up on this device: " + ", ".join(missing)
                      + " (set one up here: python -m kc attach NAME)")
            try:
                sig = signals(core, today, core_failed)
                if tz_problem:
                    sig.insert(0, ("todo", tz_problem))
            except (Exception, SystemExit) as e:
                sig = [("kc", f"FAIL: signals crashed ({e})")]
            try:
                from . import templates
                sig += templates.signals(core, seconds=min(40, end - time.monotonic()))
            except SystemExit:
                pass
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
