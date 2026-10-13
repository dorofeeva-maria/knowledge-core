---
title: 0016 — Template-owned files are updated file by file
type: adr
updated: 2026-10-08
---

# 0016. Template-owned files are updated file by file

Status: accepted · 2026-10-08 · amends 0015 (templates: "a copy, no update channel")

## Context

ADR 0015 made templates starting copies with no update channel, because the first version
rebased every module onto template updates (force-push, blocked repos, conflicts in every module
at once). A day later a real need appeared: the study template's skills were improved three times
in one day and copied by hand into five modules each time (the `repeat:` signal). Skills, shared
assets and format tools are the template's machinery, not the module's content, and every module
made from a template should run the current machinery.

## Considered options

- **Keep copy-only; copy by hand** — no mechanism, but a manual multi-repo procedure that drifts
  and is easy to get wrong.
- **Git remote + merge/rebase of the template into modules** — what broke the first version:
  unrelated histories, conflicts in every module, rewritten history.
- **File-by-file refresh of the files a template owns** ← chosen

## Decision

- The core's template catalog lists, per template, the files it **owns** (`owned`: fnmatch
  patterns). Everything else belongs to the module. Templates and modules don't know about this.
- The registry records each module's `template` and `template_version` (the template commit its
  owned files came from). `kc new-module` records them; `kc template-bind` records them for an
  existing module (the closest template commit).
- `kc template-update T [--module M] [--dry-run] [--diff]` clones the template and, per module
  and owned file: replaces it if the module still has the version it got; adds files new in the
  template (unless the module itself once deleted that path); removes files the template dropped
  and the module never changed; **keeps** any file the module changed, and reports it only while
  the template has a change to it since the recorded version that the file does not contain yet
  (a 3-way merge would still change it); until such files, and name clashes, are resolved by
  hand, the module's `template_version` is not advanced, so every run and the start signal keep
  showing them. A file that
  equals a past template version and was last changed by the template itself (an update commit,
  or the module's creation) is just behind — after a resolved race or with a stale version — and
  is updated; one the module's own commit put there (a pinned old version, a restored file) is
  the module's decision and kept. It commits in each module with the template's log, updates
  `template_version`, and lists the files the template changed but doesn't own (`AGENTS.md`…)
  for the agent to carry over by judgment. No merge, no rebase, no history rewriting; a dirty or
  failing module is skipped without blocking the others. Pushing is left to `kc sync`.
- `kc sync` checks that `ecosystem/registry.yml` still loads after pulling and before pushing
  the core: a registry kc cannot read is never pushed.
- The session-start hook reports `template:` when a template is ahead of its modules (one
  `ls-remote` per template, within what is left of the hook's time budget). The agent shows the dry run; the update runs on the human's yes.
  The hooks never update modules themselves.

## Consequences

- \+ One command delivers template fixes to every module; local adaptations survive.
- \+ Works for any template, not only study.
- \− A module that edits an owned file stops receiving that file's updates until the agent brings
  them in by hand (reported on every run as "differs locally").
- \− Mixed files (AGENTS.md: template rules + the module's own) stay a judgment task.
- \− One more network call at session start per template in use.
