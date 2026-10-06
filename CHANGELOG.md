# Changelog

Notable changes to the engine, newest first. Format: [Keep a Changelog](https://keepachangelog.com/);
decisions behind changes are in `docs/adr/`.

## Unreleased

### Added
- `ecosystem/todo/` (pending work, one file per item), `ecosystem/decisions.md`, `kc todo`
  (stubs leftover inbox/drafts files, lists items; replaces `kc check-drafts`),
  `skills/todo.md`; automatic `kc` changes are committed as `auto: …`. (ADR 0005)
- `kc update NAME` / `kc detach NAME [--yes]`; `skills/update.md` (resolve an update, adapt
  content); registry field `upstream`; AGENTS.md section *Session start*. (ADR 0003)
- AGENTS.md *Large tasks*: estimate scale, then background / now / defer. (ADR 0004)

### Removed
- `ecosystem/log.md`, `ecosystem/journal.md`, `ecosystem/candidates.md`, `kc check-drafts`.
  **Migration:** move open candidates to todo items (`kind: candidate`); keep old log/journal
  content in git history or fold key decisions into `decisions.md`. (ADR 0005)

### Changed
- `inbox/` and `drafts/` contents are committed (were gitignored). (ADR 0005)
- Fork model: one branch `main`, remotes `origin` + `upstream`; `kc pull-all` rebases onto
  origin, then onto upstream (updates always applied; conflicts block the repo); pushes are
  force-with-lease with an "includes origin" check; rerere enabled. (ADR 0003)
  **Migration:** in an existing core or module on `working`: `git branch -m working main`
  (delete the old `main` mirror first), `git push -u origin main`, set the origin's default
  branch to `main`; add `upstream: <template-url>` to each templated module in the registry.
- The orchestrator fork is now called **core** (was *center*): `KC_CORE`, `kc/core.py`,
  core-scoped commands. Re-run `kc bootstrap` to regenerate launchers. (ADR 0002)
- ADRs use MADR-lite (adds *Considered options*) and are written whenever a choice changes
  structure, a contract or agent behavior; documentation layers defined in `docs/README.md`.
  (ADR 0001)
