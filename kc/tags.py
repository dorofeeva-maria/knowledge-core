"""kc tags — the shared tag vocabulary across modules (ADR 0011).

Modules only carry `tags: [...]` in their notes' frontmatter and know nothing of the vocabulary.
The core keeps `ecosystem/tags.yml` (tag → description) and searches notes by tag across the
modules present on this device. Tags are how the core sees that notes in different modules are
related — there are no links between modules.
"""
import re
from pathlib import Path

from . import core as C

SKIP_DIRS = {".git", ".obsidian", ".claude", ".cursor", "node_modules", "__pycache__", "media"}
TAG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = {"private": "Personal: never carry details into other modules or anything public — "
                       "mention it only in general terms (ADR 0011)."}


def vocabulary(core):
    f = core / "ecosystem" / "tags.yml"
    data = (C._yaml().safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}) or {}
    return {**RESERVED, **(data.get("tags") or {})}


def note_tags(text):
    """Tags from YAML frontmatter: `tags: [a, b]` or a `tags:` block list."""
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end < 0:
        return []
    lines = text[3:end].splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^tags:\s*(.*)$", line)
        if not m:
            continue
        v = m.group(1).strip()
        if v.startswith("["):
            return [t.strip().strip("\"'") for t in v.strip("[]").split(",") if t.strip()]
        out = []
        for nxt in lines[i + 1:]:
            mm = re.match(r"^\s*-\s*(.+)$", nxt)
            if not mm:
                break
            out.append(mm.group(1).strip().strip("\"'"))
        return out
    return []


def _title(text, p):
    m = re.search(r"^title:\s*(.+)$", text[:2000], re.M)
    return m.group(1).strip().strip("\"'") if m else p.stem


def scan(core):
    """[(module, private_module, rel_path, title, tags)] for notes of present modules."""
    out = []
    for m in C.resolve(core)[0]:
        if m["status"] == "disconnected" or not m["path"] or not Path(m["path"]).exists():
            continue
        root = Path(m["path"])
        for p in root.rglob("*.md"):
            rel = p.relative_to(root)
            if set(rel.parts[:-1]) & SKIP_DIRS:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            tags = note_tags(text)
            if tags:
                out.append((m["name"], m["private"], rel.as_posix(), _title(text, p), tags))
    return out


def run(core, tag=None):
    vocab, notes = vocabulary(core), scan(core)
    if tag:
        hits = [n for n in notes if tag in n[4]]
        desc = vocab.get(tag)
        print(f"#{tag}" + (f" — {desc}" if desc else "  (not in ecosystem/tags.yml)"))
        for mod, priv, rel, title, tags in sorted(hits):
            mark = " [private]" if priv or "private" in tags else ""
            print(f"  {mod}: {rel} — {title}{mark}")
        if not hits:
            print("  no notes")
        return 0
    counts = {}
    for _, _, _, _, tags in notes:
        for t in tags:
            counts[t] = counts.get(t, 0) + 1
    unknown = sorted(t for t in counts if t not in vocab)
    bad = sorted(t for t in counts if not TAG.match(t))
    for t in sorted(vocab):
        print(f"  {t:20} {counts.get(t, 0):4}  {vocab[t] or ''}")
    if unknown:
        print("not in the vocabulary (add to ecosystem/tags.yml or rename): " + ", ".join(unknown))
    if bad:
        print("not kebab-case: " + ", ".join(bad))
    return 1 if unknown or bad else 0
