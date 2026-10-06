---
title: Apply a template/engine update
type: skill
updated: 2026-10-06
description: Resolve a template/engine update after sync, or detach; then adapt content to new rules.
---

# Skill: update

Run when the session-start report (`kc pull-all`) shows `UPDATE CONFLICT`, `UPDATE APPLIED` or
`REBASE IN PROGRESS` for the core or a module. Updates are always applied; the only ways out of a
conflict are resolving it or detaching the repo from its template (ADR 0003).

## A. Conflict — the repo is blocked

Do not write to that repo until this section is done.

1. Tell the human which repo, which update (`old..new`) and which files conflict.
2. Offer two ways:
   - **Resolve now** — run `kc update NAME` (`core` for the core). The rebase stops at each
     conflicting commit. For every conflicted file, show the human both sides, propose a
     merge that keeps the template's new rule **and** the module's own content, and apply it
     once they agree. Then `git -C <path> add <file>` and run `kc update NAME` again to continue.
     Repeat until it reports "rebase finished". git rerere remembers each resolution.
   - **Detach** — run `kc detach NAME` and show the human its warning verbatim. Only on explicit
     confirmation run `kc detach NAME --yes`, then commit the core's registry/instance change.
3. If the human wants neither right now, the repo stays blocked; work elsewhere is fine.

## B. Applied — adapt content to the new rules

1. Read the update: `git -C <path> log --oneline OLD..NEW` and `git -C <path> diff OLD NEW`
   (the range is printed in the report).
2. Find what the update asks of existing content: new or renamed folders, new frontmatter
   fields, naming rules, file formats, changed instructions. For the core, also check new or
   changed skills and `kc` commands the human should know about.
3. Compare with the repo's current content. If nothing needs to change, say so in one line.
4. Otherwise describe the adaptation (what changes, where, why) and its scale. Apply the
   **Large tasks** rule from `AGENTS.md`: background / now / defer. When deferring, say what
   it affects (e.g. "new notes will follow the new layout, old ones won't until adapted") and
   record it in `ecosystem/candidates.md` as `pending-adaptation` with the update range.
5. Adaptations are content edits: make them with the human's approval, in the repo's own
   format, then lint/index as in `close`.

## C. Push

An applied update rewrites the repo's history. Push it with `kc push-all` after the human
confirms (as part of `close`, or right away if the human asks). If push reports that origin
moved, run `kc pull-all` and push again.
