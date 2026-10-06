---
title: Process the inbox
type: skill
updated: 2026-10-06
description: Turn raw dropped material (links, docs, text, media) into distilled module content.
---

# Skill: inbox

Process everything in `inbox/` into the right modules. Run from the core. Raw material is
never committed as-is — only distilled notes land in modules.

## Steps

1. List what's waiting: the files in `inbox/` (and their items in `ecosystem/todo/`, if any).
2. For each item: read it, fetch the link, or transcribe the media as needed. **Keep media
   originals** and store transcripts beside them — never delete media.
3. Decide the target module and write the distilled knowledge there, exactly as in the
   `close` skill's **Route** step (module format, module rules, no cross-module links,
   respect `external` write zones). Prefer updating an existing note over a near-duplicate.
4. Ask the human when the destination is unclear, when an item is sensitive, or when it
   concerns a person who is not clearly identified.
5. Remove the processed inbox items (keep media). Hand off to `close` for reconcile / lint /
   commit / push, or perform those steps directly if you are closing now.
