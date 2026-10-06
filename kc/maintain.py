"""Module-scoped maintenance: generated index + mechanical lint for ONE module.

Links are intra-module only by design — there are no cross-module links.
"""
import re
import datetime
from pathlib import Path, PurePosixPath
from collections import defaultdict

LINK = re.compile(r"\[\[([^\]|#]*?)\\?(#[^\]|]*)?(\\?\|[^\]]*)?\]\]")
REQUIRED = ("title", "type", "updated")
SKIP_DIRS = (".git", ".claude", ".cursor", ".obsidian", "node_modules", "__pycache__")
SKIP_FILES = ("index.md", "log.md", "CLAUDE.md", "AGENTS.md", "README.md")
INDEX_HEADER = "<!-- auto-generated index — regenerate after adding/removing notes; do not edit by hand -->"
# Terms that must not appear inside a module/template repo (it must read as standalone).
ECO_TERMS = re.compile(
    r"\b(ecosystem|knowledge-core|registry|kc|KC_[A-Z]+|ensure-wrappers|add-agent|bootstrap|"
    r"devices\.local|upstream|core|fork)\b", re.I)
SCAN_SUFFIXES = (".md", ".txt", ".yml", ".yaml", ".py", ".sh", ".toml")


def md_files(root):
    out = []
    for p in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        out.append(p)
    return out


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
        s = re.sub(r"^\*\*TL;DR\*\*\s*[—:-]?\s*", "", s)
        s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)
        s = s.replace("**", "").replace("`", "")
        return (s[:157] + "…") if len(s) > 160 else s
    return ""


def norm(path):
    out = []
    for x in path.split("/"):
        if x in ("", "."):
            continue
        if x == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(x)
    return "/".join(out)


def build_index(root):
    groups = defaultdict(list)
    for p in sorted(md_files(root)):
        r = p.relative_to(root).as_posix()
        if PurePosixPath(r).name in SKIP_FILES:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text) or {}
        title = fm.get("title") or p.stem
        group = str(PurePosixPath(r).parent)
        s = summary_line(text)
        groups["." if group == "." else group].append(
            f"- [[{r[:-3]}|{title}]]" + (f" — {s}" if s else "")
        )
    name = root.resolve().name
    lines = [INDEX_HEADER, "", f"# {name} — index", ""]
    for g in sorted(groups, key=lambda x: (x != ".", x)):
        lines += [f'## {"(root)" if g == "." else g}', ""] + groups[g] + [""]
    out = root / "index.md"
    new = "\n".join(lines)
    old = out.read_text(encoding="utf-8") if out.exists() else None
    if old != new:
        out.write_text(new, encoding="utf-8", newline="\n")
        return True
    return False


def cmd_index(root):
    changed = build_index(root)
    print(f"index: {'updated' if changed else 'ok (no change)'} ({root.resolve().name})")


def lint(root, verbose):
    files = md_files(root)
    existing = {p.relative_to(root).as_posix() for p in files}
    by_base = defaultdict(set)
    for r in existing:
        name = PurePosixPath(r).name
        by_base[name].add(r)
        by_base[name.rsplit(".", 1)[0]].add(r)
    problems = []
    for p in files:
        r = p.relative_to(root).as_posix()
        if PurePosixPath(r).name in ("CLAUDE.md", "AGENTS.md", "README.md", "log.md"):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if PurePosixPath(r).name != "index.md":
            fm = frontmatter(text)
            if fm is None:
                problems.append((r, "no frontmatter"))
            else:
                for k in REQUIRED:
                    if not fm.get(k):
                        problems.append((r, f"frontmatter: missing {k}"))
                if fm.get("updated") and not re.match(r"^\d{4}-\d{2}-\d{2}$", fm["updated"]):
                    problems.append((r, f"frontmatter: bad updated {fm['updated']!r}"))
        body = re.sub(r"```.*?```", "", text, flags=re.S)
        d = str(PurePosixPath(r).parent)
        for m in LINK.finditer(body):
            tg = m.group(1).strip()
            if not tg:
                continue
            if "/" not in tg:
                ok = tg in by_base or tg.removesuffix(".md") in by_base
            else:
                ok = any(
                    c and (c in existing or c + ".md" in existing)
                    for c in (norm(d + "/" + tg), norm(tg))
                )
            if not ok:
                problems.append((r, f"broken link [[{tg}]]"))
    if not (root / "index.md").exists():
        problems.append((".", "index.md missing — run: kc index"))
    label = root.resolve().name
    if not problems:
        print(f"lint {label}: ok")
    else:
        kinds = defaultdict(int)
        for _, msg in problems:
            kinds[msg.split(" [[")[0].split(":")[0]] += 1
        detail = ", ".join(f"{v} {k}" for k, v in sorted(kinds.items(), key=lambda x: -x[1]))
        print(f"lint {label}: {len(problems)} problems ({detail})" + ("" if verbose else " — add -v for details"))
    if verbose:
        for r, msg in problems:
            print(f"  {r}: {msg}")
    return len(problems)


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


def compact_log(path, keep):
    """Mechanical half of log compaction: move all but the last `keep` entries into a
    sibling .archive file, leaving a marker. The judgment half (rewriting the archived bulk
    into a compact summary that preserves decisions + current state) is the compact-log skill.
    """
    p = Path(path)
    if not p.exists():
        print(f"compact-log: {path} not found")
        return
    lines = p.read_text(encoding="utf-8").splitlines()

    def is_entry(s):
        return bool(s.strip()) and not s.lstrip().startswith("#")

    idx = [i for i, s in enumerate(lines) if is_entry(s)]
    if len(idx) <= keep:
        print(f"compact-log: {len(idx)} entries ≤ keep={keep} — nothing to do")
        return
    header = lines[:idx[0]]
    entries = [lines[i] for i in idx]
    old, recent = entries[:-keep], entries[-keep:]
    today = datetime.date.today().isoformat()
    archive = p.with_name(p.stem + ".archive" + p.suffix)
    with archive.open("a", encoding="utf-8") as f:
        f.write(f"\n<!-- archived {today}: {len(old)} entries -->\n" + "\n".join(old) + "\n")
    marker = (f"<!-- {len(old)} older entries archived in {archive.name} on {today}; "
              f"summarize with the compact-log skill, preserving decisions -->")
    p.write_text("\n".join(header + [marker, ""] + recent) + "\n", encoding="utf-8", newline="\n")
    print(f"compact-log: archived {len(old)} entries to {archive.name}, kept {len(recent)}")
