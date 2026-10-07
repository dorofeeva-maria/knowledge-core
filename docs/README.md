# docs/

Each fact lives in **one** place; other places link to it.

| Layer | Reader | Answers | Where |
|-------|--------|---------|-------|
| **Instructions** | the agent | what to do | `AGENTS.md` |
| **Explanation** | a human | how it works now | `docs/architecture.md`, `docs/glossary.md` |
| **How-to** | a human | how to get X done | `docs/setup.md`, `docs/templates.md` |
| **Reference** | both | exact commands and file formats | `python3 -m kc --help`, `ecosystem/README.md` |
| **Decisions** | anyone | why it is this way | `docs/adr/` |
| **Changes** | anyone | what changed when | `CHANGELOG.md` |

Instructions never retell design history; explanation and how-to describe the current state and
are updated in the same commit as the ADR that changes it.
