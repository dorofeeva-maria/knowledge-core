# knowledge-core — agent instructions (canon)

This is the canonical, AI-agnostic instruction entry. **Any** assistant reads this file.
Assistant-specific wrappers (e.g. Claude's `CLAUDE.md` / slash commands) are thin pointers
generated from here by `adapters/`.

## Two layers

- **Mechanical → `kc` CLI.** Deterministic plumbing (lint, index, pull, commit/push,
  registry, wrapper generation). Call it; don't reimplement it. See `kc/`.
- **Cognitive → skills.** Judgment-based operations are markdown instructions in `skills/`.
  Follow the relevant skill; it tells you when to call `kc`.

## Operations

| Operation | Layer | Where |
|-----------|-------|-------|
| close a session (route knowledge, reconcile, commit) | skill | `skills/close.md` *(TBD)* |
| process inbox / raw drop | skill | `skills/inbox.md` *(TBD)* |
| emergence (propose module / extraction / split) | skill | `skills/emergence.md` *(TBD)* |
| index, lint, check | CLI | `kc index|lint|check` |

## Ground rules

- Modules are independent and know nothing of the ecosystem; never add cross-module links.
- Write only within the current module; cross-module moves happen through the center.
- Propose structural changes (new module, extraction, split) — the human decides.
- Automatic (no approval): mechanical whitelist only. Content edits are gated.

> Scaffold in progress — skill files and the full ruleset are being added incrementally.
