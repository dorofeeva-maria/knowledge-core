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
| close a session (route knowledge, reconcile, commit, push) | skill | `skills/close.md` |
| process inbox / raw drop | skill | `skills/inbox.md` |
| emergence (propose module / extraction / split) | skill | `skills/emergence.md` |
| index, lint, check | CLI | `kc index\|lint\|check` |
| registry, pull-all, commit-push, push-all, check-drafts | CLI | `kc <cmd>` |
| HOME map, compact-log, check-template | CLI | `kc home`, `kc compact-log`, `kc check-template` |
| create a module / list templates | CLI | `kc new-module`, `kc templates` |
| set up this device | CLI | `kc bootstrap` |
| per-AI wrappers | CLI | `kc ensure-wrappers --agent NAME`, `kc add-agent NAME` |

## Ground rules

- Modules are independent and know nothing of the ecosystem; never add cross-module links.
- Write only within the current module; cross-module moves happen through the core.
- Propose structural changes (new module, extraction, split) — the human decides.
- Automatic (no approval): mechanical whitelist only. Content edits are gated.
- Sessions run from the **core**; it may write into modules (except `external` ones,
  which are limited to their registry `write_zones`). Opening a module alone is standalone
  mode: follow that module's own rules; ecosystem orchestration is simply absent.
