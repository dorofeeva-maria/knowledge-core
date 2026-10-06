---
title: 0015 — Large files are not stored; distill, then delete
type: adr
updated: 2026-10-07
---

# 0015. Large files are not stored; distill, then delete

Status: accepted · 2026-10-07 (supersedes the large-file handling of 0007)

## Context

ADR 0007 kept files over `large_file_mb` in `<media>/large/`, gitignored and on one device. But a
large file anywhere else — dropped in `inbox/`, in a module's `media/` root, in any repo — is not
ignored, so the repo is permanently dirty and `sync` skips it forever ("skipped (uncommitted
changes)"); a committed `todo` stub for it travels to devices that do not have the file; and
changing a module's `media` setting did not update the `.gitignore`. More fundamentally, keeping
large originals at all — even gitignored, even on one device — was not wanted: the ecosystem
should hold the distilled knowledge, not the big binaries.

## Considered options

What to do with a large file: keep it in `<media>/large/` (0007) · Git LFS · **never store it —
distill it into notes and delete the original, or delete it** ← chosen.

When one is encountered: leave it (dirties the repo, blocks sync) · auto-move it to a stash
(intrusive, breaks links) · **refuse to commit it and ask the human to distill-then-delete or
delete** ← chosen.

A large file you still want verbatim: **keep it outside module repos; the ecosystem does not hold
it** ← chosen · a gitignored in-repo stash.

## Decision

Files over `large_file_mb` (instance setting, default 20) are never committed or stored; there is
no `<media>/large/`. When `kc` finds one in a repo it does not commit: `commit-push` reports
`blocked — large file(s) not stored …`, and session-start `pull-all` flags it (`large file not
stored …`); `kc todo` does not stub it. The human distills it into notes and deletes the original,
or deletes it; `close` does not finish while one is unresolved. Only the distilled notes are kept.
A large file you want to keep verbatim lives outside module repos. The `media` setting still keeps
small media in `media/`; the `<media>/large/` folder and its `.gitignore` rule are removed from the
template and `kc`.

## Consequences

- \+ No large file silently blocks sync or travels as a dangling todo.
- \+ The ecosystem holds distilled knowledge, not big binaries.
- \− A large source you want verbatim must be kept outside the ecosystem.
- \− A large file must be processed (or deleted) before `close` or a commit can proceed.
