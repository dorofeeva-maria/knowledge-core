"""Session drafts and assistant hooks (see ADR 0006).

The draft of a session is a raw transcript of the conversation — the human's messages and the
assistant's replies, no tool noise — kept in `drafts/<date>-<session8>.md` and committed +
pushed as it grows. No AI is involved: an assistant's adapter tells kc where its transcript
is and how to read it. Capture runs in the background every N turns or M minutes (Stop hook),
and in the foreground before compaction and at session end.

A draft exists ⇔ its session has unprocessed content. `close` routes the draft into modules and
deletes it; the per-session offset (local state) remembers how far the transcript was
processed, so a resumed session starts a fresh draft from there.
"""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import core as C
from . import gitsync as G

STATE = ".kc"                      # gitignored, per device
LOCK_STALE = 300


# ---------------------------------------------------------------- local state
def _state_dir(core):
    d = core / STATE / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_state(core, sid):
    f = _state_dir(core) / f"{sid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_state(core, sid, st):
    (_state_dir(core) / f"{sid}.json").write_text(json.dumps(st, indent=1), encoding="utf-8")


def current(core):
    f = core / STATE / "current.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def set_current(core, data):
    (core / STATE).mkdir(exist_ok=True)
    (core / STATE / "current.json").write_text(json.dumps(data, indent=1), encoding="utf-8")


def _settings(core):
    inst = C.load_instance(core)
    return int(inst.get("draft_every_turns", 5)), int(inst.get("draft_every_minutes", 15))


# ---------------------------------------------------------------- drafts
def draft_path(core, sid, create_date=None):
    found = sorted((core / "drafts").glob(f"*-{sid[:8]}.md"))
    if found:
        return found[0]
    date = create_date or datetime.date.today().isoformat()
    return core / "drafts" / f"{date}-{sid[:8]}.md"


def _adapter_transcript(core, agent):
    from .wrappers import _adapter
    return (_adapter(core, agent) or {}).get("transcript") or {}


def _read_claude_jsonl(path, start, include_tools):
    """Return (markdown, new_offset) for transcript lines [start:]."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    out, tool_names = [], {}
    for raw in lines[:start]:                 # remember tool names for results we'll meet
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        for b in ((d.get("message") or {}).get("content") or []) if isinstance(
                (d.get("message") or {}).get("content"), list) else []:
            if b.get("type") == "tool_use":
                tool_names[b.get("id")] = b.get("name")
    for raw in lines[start:]:
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if d.get("isSidechain") or d.get("isMeta") or d.get("type") not in ("user", "assistant"):
            continue
        content = (d.get("message") or {}).get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        for b in blocks:
            t = b.get("type")
            if t == "tool_use":
                tool_names[b.get("id")] = b.get("name")
            elif t == "text":
                text = (b.get("text") or "").strip()
                if not text or text.startswith(("<command-", "<local-command", "<system-reminder")):
                    continue
                who = "Human" if d["type"] == "user" else "Assistant"
                out.append(f"**{who}:** {text}")
            elif t == "tool_result" and tool_names.get(b.get("tool_use_id")) in include_tools:
                c = b.get("content")
                text = c if isinstance(c, str) else "\n".join(
                    x.get("text", "") for x in (c or []) if isinstance(x, dict))
                if text.strip():
                    out.append(f"**Human (answer):** {text.strip()}")
    return "\n\n".join(out), len(lines)


READERS = {"claude-jsonl": _read_claude_jsonl}


def capture(core, sid=None, force=False, push=True):
    """Append the new part of the session transcript to its draft. Returns the draft path or None."""
    cur = current(core)
    sid = sid or cur.get("session_id")
    if not sid:
        print("draft: no current session")
        return None
    st = load_state(core, sid)
    transcript = st.get("transcript") or cur.get("transcript_path")
    agent = st.get("agent") or cur.get("agent")
    if not transcript or not Path(transcript).exists():
        print("draft: transcript not available for this assistant/session")
        return None
    lock = core / STATE / f"capture-{sid[:8]}.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > LOCK_STALE:
            lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL)
        os.close(fd)
    except FileExistsError:
        return None
    try:
        spec = _adapter_transcript(core, agent)
        reader = READERS.get(spec.get("format"))
        if not reader:
            print(f"draft: no transcript reader for '{agent}'")
            return None
        text, offset = reader(transcript, st.get("offset", 0), spec.get("include_tool_results") or [])
        st.update(offset=offset, turns=0, last_capture=time.time())
        save_state(core, sid, st)
        if not text:
            return None
        d = draft_path(core, sid)
        today = datetime.date.today().isoformat()
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if not d.exists():
            d.parent.mkdir(exist_ok=True)
            head = (f"---\ntitle: Session draft {sid[:8]}\ntype: draft\nsession: {sid}\n"
                    f"agent: {agent}\ncreated: {today}\nupdated: {today}\n---\n\n"
                    f"Raw transcript of an open session; `close` routes it into modules and deletes it.\n")
        else:
            head = ""
        with d.open("a", encoding="utf-8", newline="\n") as f:
            f.write(head + f"\n## {stamp}\n\n{text}\n")
        rel = d.relative_to(core).as_posix()
        G.auto_commit(core, [rel], f"draft {sid[:8]} +{stamp}", and_push=push)
        return d
    finally:
        lock.unlink(missing_ok=True)


def _spawn_capture(core, sid):
    """Run `kc draft --session SID` detached so the hook returns immediately."""
    args = [sys.executable, "-m", "kc", "draft", "--session", sid]
    env = {**os.environ, "KC_CORE": str(core),
           "PYTHONPATH": str(Path(__file__).resolve().parent.parent) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen(args, **kw)


# ---------------------------------------------------------------- hooks
def _stdin_json():
    try:
        data = sys.stdin.read()
        return json.loads(data) if data.strip() else {}
    except (ValueError, OSError):
        return {}


def hook(core, event, agent):
    ev = _stdin_json()
    sid = ev.get("session_id") or current(core).get("session_id")
    if event == "session-start":
        return _on_start(core, agent, ev)
    if not sid:
        return 0
    st = load_state(core, sid)
    if event == "stop":
        every_turns, every_min = _settings(core)
        st["turns"] = st.get("turns", 0) + 1
        st["last_seen"] = time.time()
        save_state(core, sid, st)
        due = st["turns"] >= every_turns or time.time() - st.get("last_capture", 0) >= every_min * 60
        if due:
            _spawn_capture(core, sid)
        return 0
    if event == "pre-compact":
        capture(core, sid, force=True)
        return 0
    if event == "session-end":
        capture(core, sid, force=True)
        st = load_state(core, sid)
        st["ended"] = True
        save_state(core, sid, st)
        d = draft_path(core, sid)
        if d.exists():
            sys.stderr.write("Session ended without `close`: its transcript is saved in "
                             f"{d.relative_to(core).as_posix()} and will be offered at the next start.\n")
            return 2
        return 0
    return 0


ACTIVE_MINUTES = 30


def _other_live_session(core, sid):
    """One session at a time per core (ADR 0010): is another one still running here?"""
    prev = current(core).get("session_id")
    if not prev or prev == sid:
        return None
    st = load_state(core, prev)
    if st.get("ended") or time.time() - st.get("last_seen", 0) > ACTIVE_MINUTES * 60:
        return None
    return prev


def _on_start(core, agent, ev):
    sid = ev.get("session_id")
    other = _other_live_session(core, sid) if sid else None
    if other:
        print(f"WARNING: another session ({other[:8]}) was active in this core in the last "
              f"{ACTIVE_MINUTES} minutes. Run one session per core at a time: close the other one "
              f"first, or work elsewhere — kc commits everything in a repo.")
    if sid:
        st = load_state(core, sid)
        st.setdefault("offset", 0)
        st.update(agent=agent, transcript=ev.get("transcript_path") or st.get("transcript"))
        st.setdefault("last_capture", time.time())
        st["last_seen"] = time.time()
        st.pop("ended", None)
        save_state(core, sid, st)
        set_current(core, {"session_id": sid, "transcript_path": st["transcript"], "agent": agent})
    from . import wrappers, repos, todo
    repos.pull_all(core)                  # first, so wrappers are built from the updated canon
    wrappers.ensure_wrappers(core, agent)
    todo.run(core)
    if sid:
        d = draft_path(core, sid)
        if ev.get("source") in ("resume", "compact") and d.exists():
            print(f"session: continuing — this session's draft is {d.relative_to(core).as_posix()}")
        else:
            print(f"session: new — draft will be {d.relative_to(core).as_posix()} "
                  f"(captured automatically; `close` processes it)")
    return 0
