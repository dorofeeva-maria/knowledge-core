"""kc todo — the core's list of pending work (see ADR 0005).

One file per item in `ecosystem/todo/`. Agents create items for candidates, adaptations and
deferred tasks; `kc todo` itself creates a stub for every file left in `inbox/` or `drafts/`
that has no item yet (they were not processed by `close`). It then prints a summary for the
agent to walk through with the human (skills/todo.md).
"""
import datetime
import re
from pathlib import Path
from . import gitsync as G
from . import maintain

KINDS = ("inbox", "draft", "candidate", "adaptation", "task")
SOURCES = {"inbox": "inbox", "drafts": "draft"}


def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:50] or "item"


def todo_dir(core):
    return core / "ecosystem" / "todo"


def items(core):
    out = []
    d = todo_dir(core)
    if d.exists():
        for p in sorted(d.glob("*.md")):
            if p.name == "README.md":
                continue
            fm = maintain.frontmatter(p.read_text(encoding="utf-8", errors="replace")) or {}
            out.append((p, fm))
    return out


def _raw_files(core, folder):
    d = core / folder
    if not d.exists():
        return []
    return [p for p in sorted(d.rglob("*"))
            if p.is_file() and p.name != "README.md" and not p.name.startswith(".")]


def stub_leftovers(core):
    """Create a todo stub for each inbox/drafts file that has none. Returns created paths."""
    known = {fm.get("source") for _, fm in items(core)}
    from .session import current, draft_path
    sid = current(core).get("session_id")
    if sid:   # the running session's own draft is not a leftover
        known.add(draft_path(core, sid).relative_to(core).as_posix())
    today = datetime.date.today().isoformat()
    created = []
    for folder, kind in SOURCES.items():
        for f in _raw_files(core, folder):
            src = f.relative_to(core).as_posix()
            if src in known:
                continue
            p = todo_dir(core) / f"{today}-{kind}-{_slug(f.stem)}.md"
            n = 2
            while p.exists():
                p = todo_dir(core) / f"{today}-{kind}-{_slug(f.stem)}-{n}.md"
                n += 1
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                f"---\ntitle: Process {src}\ntype: todo\nkind: {kind}\nsource: {src}\n"
                f"target: \ncreated: {today}\nupdated: {today}\n---\n\n"
                f"Left in `{folder}/` without `close`. To do: process it (see the "
                f"`{'inbox' if kind == 'inbox' else 'close'}` skill), then delete this item.\n",
                encoding="utf-8", newline="\n")
            created.append(p)
    return created


def run(core):
    created = stub_leftovers(core)
    if created:
        G.auto_commit(core, [p.relative_to(core).as_posix() for p in created] + ["inbox", "drafts"],
                      f"todo stubs for {len(created)} unprocessed inbox/drafts file(s)")
    its = items(core)
    if not its:
        print("todo: empty")
        return 0
    by_kind = {}
    for p, fm in its:
        by_kind.setdefault(fm.get("kind", "task"), []).append((p, fm))
    print(f"todo: {len(its)} pending — " + ", ".join(f"{len(v)} {k}" for k, v in by_kind.items()))
    for k, v in by_kind.items():
        for p, fm in v:
            tgt = f" → {fm['target']}" if fm.get("target") else ""
            print(f"  [{k}] {fm.get('title', p.stem)}{tgt}  ({p.name})")
    print("→ walk through it with the human (skills/todo.md): apply / defer / reject, or defer all")
    return 1
