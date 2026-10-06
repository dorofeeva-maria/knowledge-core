---
title: 0007 — Module settings and where media lives
type: adr
updated: 2026-10-06
---

# 0007. Module settings and where media lives

Status: accepted · 2026-10-06 (large-file handling superseded by 0015)

## Context

Skills said "keep media originals" but not where, so processed media stayed in the core's
inbox forever. A module's write language was "the module's own setting" with no format. Large
files bloat git history for good, and GitHub rejects files over 100 MB.

## Considered options

Where media goes: **into the main target module, `media/` by default, configurable per module or
switched off** ← chosen · an archive in the core (modules lose files when detached) · external
storage with links.

Large files: compress them in git (no gain: mp4/mp3/jpg/most PDFs are already compressed, and
git compresses objects anyway) · Git LFS for all media (1 GB free quota) · **a size limit
(default 20 MB); bigger files go to `<media>/large/`, ignored by git, kept on one device, not
linked** ← chosen.

Media used by several modules: a copy in each · **the main module only; others mention the
source in words** ← chosen.

Where module settings live:
- only in the core registry — a module opened alone does not know its rules;
- only in the module (a fixed *Settings* section) — a new requirement on every module, foreign
  repos become non-conforming, prose parsing is fragile;
- **hybrid: optional registry fields are the source of truth for the core; the same rules are
  written in plain words into the module's `AGENTS.md` when it is created; the agent proposes
  to sync them if they differ** ← chosen.

## Decision

Optional registry fields `language` and `media` (absent: session language, `media/`;
`media: false`: keep no media). The `inbox` skill moves each original into the main module's
media folder with its transcript; files over `large_file_mb` (instance setting, default 20)
go to `<media>/large/`, which the module's `.gitignore` excludes. `kc` never commits a file over
the limit: `commit-push` and automatic commits leave it out and say so. When a module is
created or promoted, the agent asks for language, private and remote (`kc new-module
--language --private --remote --media`) and writes the conventions into the module's
`AGENTS.md`. The info template ships `media/` and ignores `media/large/`.

## Consequences

- \+ Any repo can still be a module as is; settings are optional with defaults.
- \+ A module carries its media and its rules when detached or opened alone.
- \+ No file can break a push by size.
- \− Large originals exist on one device only.
- \− Settings live in two places and can drift; the agent checks them when routing.
