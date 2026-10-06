---
title: 0012 — Memory lives in plain files: core and modules
type: adr
updated: 2026-10-06
---

# 0012. Memory lives in plain files: core and modules

Status: accepted · 2026-10-06

## Context

"Stable facts about the user live in a separate memory tier" — but no place was named. In
practice the assistant's built-in memory held them (e.g. Claude's auto-memory), which another
assistant cannot read, against the engine's model-agnostic goal. Many such facts belong to one
subject (a preferred citation style belongs to a research module, not everywhere). Personal
rules for processing other people's messages had no home either.

## Considered options

- leave memory to each assistant;
- a dedicated private module "me";
- **a core file `ecosystem/memory.md` for facts that hold everywhere, plus a `memory.md` in
  modules for facts of their subject; the agent picks the module first** ← chosen.

Rules for other people's messages: instance rules file · each module · **the `inbox` skill**
← chosen (they are rules for processing raw material).

## Decision

`kc bootstrap` creates `ecosystem/memory.md`. `AGENTS.md` tells the agent to read it at session
start and a module's `memory.md` before working in that module, and to record corrections and
lasting preferences in the module whose subject they belong to, else in the core — one bullet
with a **Why:**, never in both. The info template ships `memory.md` and tells a standalone
assistant to read and maintain it. An assistant's built-in memory is at most a cache.

The `inbox` skill now says: process chats with other people fully, quotes verbatim in the
original language, tag them `private`; ask when a person is unclear or not someone the human
knows personally.

## Consequences

- \+ Any assistant, in the core or in a module alone, sees the same memory.
- \+ Subject facts travel with their module.
- \− The agent must classify each fact; misfiled facts need moving by hand.
