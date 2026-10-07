---
title: 0011 — Shared tags relate modules; privacy by module or note
type: adr
updated: 2026-10-06
---

# 0011. Shared tags relate modules; privacy by module or note

Status: accepted, partly superseded by 0015 · 2026-10-06

## Context

Modules never link to each other, so the core had no way to see that notes in different
modules are about the same person, place or topic; "a note in the core" for cross-module
relationships had no defined home. A project that used to link to a shared knowledge base needs
another way to stay connected. Privacy was a per-module flag, while real personal material
often sits in single notes of otherwise ordinary modules; two tags (`private`, `sensitive`)
meant the same thing in practice.

## Considered options

Relating modules: notes in the core · allow links to "base" modules (breaks independence) ·
**shared tags in note frontmatter** ← chosen.

Vocabulary: a list in each module, merged by the core · **one vocabulary in the core,
`ecosystem/tags.yml`** ← chosen. Format: namespaced (`person/alex`) · **plain kebab-case words**
← chosen. Count per note: 0–3 · 0–5 · **no limit** ← chosen (tags are now the only cross-module
relation).

Use by the core: **`kc tags TAG` search across modules; `kc tags` lists counts and tags missing
from the vocabulary** ← chosen; a generated tag map file — not now.

Privacy protects against: **details moving into other modules**, **leaking into anything
public** ← chosen; hiding names in the core's own output, and restricting what the agent reads —
not chosen. Level: **module flag plus a `private` note tag** ← chosen. `sensitive`: **same as
`private`, dropped** ← chosen.

## Decision

Notes may carry `tags: [kebab-case, words]` naming cross-cutting entities (people, places,
stack, level) — never the folder or type. The core keeps the vocabulary in `ecosystem/tags.yml`
(created by `bootstrap`; `private` is built in); the agent uses it when writing and adds new
tags with a one-line meaning. `kc tags TAG` lists notes with that tag in every module present on
the device; `kc tags` shows counts and unknown or malformed tags.

A module with `private: true`, or a note tagged `private`, keeps its details to itself: other
modules get only a general mention, and nothing goes into public places. The info template
documents tags and the `private` tag in plain words and its check validates the tag format.

## Consequences

- \+ The core can gather related knowledge across modules without links.
- \+ A detached module keeps meaningful tags.
- \− The vocabulary needs upkeep; `kc tags` flags drift.
- \− Notes in modules without frontmatter (other formats) cannot be tagged.
