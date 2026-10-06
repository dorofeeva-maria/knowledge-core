---
title: Process the inbox
type: skill
updated: 2026-10-06
description: Turn raw dropped material (links, docs, text, media) into distilled module content.
---

# Skill: inbox

Process everything in `inbox/` into the right modules. Run from the core. Text, links and
pasted material are distilled into notes and then deleted; media originals are kept in the
module (step 4).

## Steps

1. List what's waiting: the files in `inbox/` (and their items in `ecosystem/todo/`, if any).
2. For each item: read it, fetch the link, or transcribe the media as needed.
3. Decide the target module and write the distilled knowledge there, exactly as in the
   `close` skill's **Route** step (module format, module rules, no cross-module links,
   respect `external` write zones). Prefer updating an existing note over a near-duplicate.
   If the knowledge spreads over several modules, pick the **main** one for the original;
   the others mention the source in words, without a link.
4. **Media** (PDF, images, audio, video): move the original into the main module's media
   folder (registry `media`, default `media/`) and put its transcript beside it; the note
   links to it inside the module. Files over the size limit (`large_file_mb`, default 20 MB)
   go to `<media>/large/` — not committed, kept only on this device, not linked from notes.
   If the module has `media: false`, keep only the notes and delete the original.
5. Ask the human when the destination is unclear, when an item is sensitive, or when it
   concerns a person who is not clearly identified.
6. Remove the processed inbox items and their todo items. Hand off to `close` for reconcile /
   lint / commit, or perform those steps directly if you are closing now.
