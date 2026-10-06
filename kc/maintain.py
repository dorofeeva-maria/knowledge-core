"""Small text helpers shared by kc: frontmatter and a note's summary line.

Module formats — index, lint, log compaction — are not here: they ship with each module's
template and run through the registry field `check` (ADR 0008).
"""
import re



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
