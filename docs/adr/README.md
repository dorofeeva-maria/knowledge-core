# adr/

Architecture Decision Records for the **engine**: why the engine is built the way it is.
Format: MADR-lite (Nygard's Status · Context · Decision · Consequences plus a mandatory
**Considered options** list) — see `template.md`. Numbered, one decision per file, immutable:
a changed decision is a new ADR whose status supersedes the earlier one (the earlier one's
status line is the only edit allowed: `superseded by NNNN`).

## When a change gets an ADR

Write an ADR when **there were real alternatives** and the choice changes one of:

- the **structure** of the ecosystem (pieces, topology, where data lives, its lifecycle);
- a **contract** — a file format, a folder, a `kc` command or its flags, a config key;
- how an **agent behaves** — what a skill or `AGENTS.md` tells it to do.

No ADR for a fix with no choice in it (a bug, a typo, stale wording): fix it, describe it in the
commit message and in `CHANGELOG.md`.

## Rules

- Written in the engine when the decision is made — directly or as part of a PR to the engine.
- Generic: they record the engine's design for anyone using the template, never a particular
  user's data or migration history.
- After accepting an ADR, update the docs it affects (see `docs/README.md`) in the same commit;
  the ADR explains *why*, the docs describe *what* and *how*.
