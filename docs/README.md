# docs/

How the engine's documentation is organized. Each fact lives in **one** place; other places
link to it instead of repeating it.

| Layer | Reader | Answers | Where |
|-------|--------|---------|-------|
| **Instructions** | an AI agent | *what to do* — imperative, procedural | `AGENTS.md`, `skills/*.md` |
| **Explanation** | a human | *how it works* — the current design | `docs/architecture.md`, `docs/glossary.md` |
| **How-to** | a human | *how to get X done* — task recipes | `docs/setup.md`, `docs/templates.md` |
| **Reference** | human or agent | *exact facts* — commands, flags, file formats | `kc --help`, `ecosystem/README.md`, `adapters/README.md` |
| **Decisions** | anyone | *why it is this way* — immutable records | `docs/adr/` |
| **Changes** | anyone | *what changed when* | `CHANGELOG.md` |

Rules:

- Instructions never explain design history; they link to an ADR if the reason matters.
- Explanation and how-to describe the **current** state; when a decision changes, update them
  in the same commit as the new ADR.
- Reference is generated or kept next to the thing it describes (a command's help text, a
  file's own README).
