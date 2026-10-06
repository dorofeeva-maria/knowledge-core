---
title: Compact a log
type: skill
updated: 2026-10-06
description: Shrink an oversized log, preserving decisions and current state.
---

# Skill: compact-log

Use when any module's `log.md` has grown too large. Works on any log.

## Steps

1. Run `kc compact-log <path/to/log.md> [--keep N]`. This moves all but the last N entries
   into a sibling `*.archive.md` and leaves a marker. Recent entries stay verbatim.
2. Open the `*.archive.md` section just created and **rewrite the archived bulk into a compact
   summary**, preserving:
   - every **decision** and every **changed decision**,
   - the **current state** that still matters,
   and dropping day-to-day narrative that no longer carries information.
3. Keep the recent (kept) entries untouched.
4. Leave the summary in the archive (or fold it back under the marker if you prefer a single
   file) — your call per project, but never drop a decision.

Compaction is lossy for narrative, never for decisions or current state.
