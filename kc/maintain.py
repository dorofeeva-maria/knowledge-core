"""Small text helpers shared by kc (frontmatter, summary line) and `kc check-template`.

Module formats — index, lint, log compaction — are not here: they ship with each module's
template and run through the registry field `check` (ADR 0008).
"""
import re

SKIP_DIRS = (".git", ".claude", ".cursor", ".obsidian", "node_modules", "__pycache__")
# Terms that must not appear inside a module/template repo (it must read as standalone).
ECO_TERMS = re.compile(
    r"\b(ecosystem|knowledge-core|registry|kc|KC_[A-Z]+|ensure-wrappers|add-agent|bootstrap|"
    r"devices\.local|upstream|core|fork)\b", re.I)
SCAN_SUFFIXES = (".md", ".txt", ".yml", ".yaml", ".py", ".sh", ".toml")


def frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    kv = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            kv[m.group(1)] = m.group(2).strip().strip("\"'")
    return kv


def summary_line(text):
    """First meaningful prose line after frontmatter / TL;DR heading."""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        body = text[end + 4:] if end >= 0 else text
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ">", "|", "```", "<", "---")):
            continue
        s = re.sub(r"^(\*\*)?TL;DR(\*\*)?\s*[—:-]?\s*", "", s)
        s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)
        s = s.replace("**", "").replace("`", "")
        return (s[:157] + "…") if len(s) > 160 else s
    return ""


def check_template(root):
    """Flag ecosystem references in a template/module repo — it must read as standalone.
    Advisory: reports matches for review (some words can be legitimate content)."""
    hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in SCAN_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if ECO_TERMS.search(line):
                hits.append((p.relative_to(root).as_posix(), i, line.strip()))
    if not hits:
        print(f"check-template {root.name}: ok — no ecosystem references")
        return 0
    print(f"check-template {root.name}: {len(hits)} possible ecosystem reference(s) — "
          f"a module repo must not mention the ecosystem; review:")
    for f, i, line in hits:
        print(f"  {f}:{i}: {line[:100]}")
    return len(hits)
