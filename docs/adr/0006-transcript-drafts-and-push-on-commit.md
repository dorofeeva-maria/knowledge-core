---
title: 0006 — Session drafts are captured transcripts; every commit is pushed
type: adr
updated: 2026-10-06
---

# 0006. Session drafts are captured transcripts; every commit is pushed

Status: superseded by 0015 · 2026-10-06

## Context

The only rule for drafts was "a light draft in `drafts/`": nobody said who writes it, when, or
in what form, and an agent that forgets to write loses the session when it ends without
`close`. Session end cannot be blocked (in Claude Code the end hook runs briefly and cannot stop
an exit; closing the terminal may skip it). Drafts and other core changes reached the other
devices only after a push, and pushing waited for a confirmation in `close`. A resumed session
had no way to know whether its content had already been processed.

## Considered options

What the draft is:
- the agent writes a distilled draft as each piece settles — depends on the agent remembering;
- distilled draft plus a raw transcript as a safety net;
- a background AI distills each segment — costs tokens, can still miss things;
- **a raw transcript captured by `kc` without AI; `close` distills it** ← chosen.

When it is captured: every turn · **every 5 turns or 15 minutes, in the background (Stop hook),
plus before compaction and at session end** ← chosen · every 10 turns / 30 minutes.

Exit without `close`: warn only · **save the transcript, then warn** ← chosen.

Resume: a closed-session marker · **the draft itself: it exists ⇔ the session has unprocessed
content; `close` deletes it; a per-session offset remembers how far the transcript was
processed** ← chosen.

Push: only in `close` after confirmation · only the core · **every commit is pushed right
away; confirmation only for external modules and for changes proposed to a template or the
engine** ← chosen.

## Decision

Each session has one draft, `drafts/<date>-<session8>.md`, holding the raw conversation (the
human's messages, the assistant's replies, and the human's answers to the assistant's
questions; no tool output). `kc` appends to it from the assistant's transcript, located and
parsed as the adapter declares (`transcript:` in `adapter.yml`). Capture runs detached from the
Stop hook every `draft_every_turns` turns or `draft_every_minutes` minutes (instance settings,
default 5 / 15), and in the foreground on pre-compact and session end; each capture is
committed and pushed (`auto:`). The end hook warns if a draft remains. `kc todo` turns drafts of
other sessions into todo items; the running session's own draft is skipped. `close` flushes the
draft (`kc draft`), routes it, and deletes it; a per-device offset in `.kc/` lets a resumed
session start a fresh draft from where `close` stopped.

`kc commit-push` and every `auto:` commit push immediately. External modules are committed but
pushed only with `kc push-external NAME` after the human confirms; proposals to a template or the
engine also need confirmation.

Adapters may own hooks: list entries whose command starts with `kc ` are replaced on each
`ensure-wrappers`, so changed commands never leave stale copies.

## Consequences

- \+ Nothing said in a session is lost, even without `close` or with an agent that forgets.
- \+ Every device sees the latest state; no push step to forget.
- \+ Works without AI cost; distillation happens once, in `close`.
- \− The core holds full conversation transcripts — it must stay private.
- \− Assistants without a readable transcript get no automatic draft.
- \− One `current` session per core per device: two parallel sessions in the same core share
  the pointer used by `kc draft` without `--session`.
