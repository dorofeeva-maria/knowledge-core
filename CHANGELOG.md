# Changelog

Notable changes to the engine, newest first. Format: [Keep a Changelog](https://keepachangelog.com/);
decisions behind changes are in `docs/adr/`.

## Unreleased

### Fixed
- Wrappers of removed skills are deleted; the start hook syncs repos before regenerating
  wrappers; wording of the language override, the default catalog and the write rule.

### Added
- Memory in plain files: `ecosystem/memory.md` (bootstrap) + modules' `memory.md`; AGENTS.md
  *Memory*; inbox rules for other people's messages. (ADR 0012)
- Shared tags: `ecosystem/tags.yml` vocabulary (created by bootstrap), `kc tags [TAG]`;
  privacy by module flag or `private` note tag. (ADR 0011)
- `kc set NAME key=value`; AGENTS.md *During the session* (write on request, one session per
  core); start hook warns about another active session. (ADR 0010)
- `kc add-module NAME PATH` registers an existing repo (own or `--external`). (ADR 0009)
- Module contract check in `kc pull-all` (`MISMATCH` lines) and the module's own format check
  (registry/catalog field `check`, `kc new-module --check`). (ADR 0008)
- Module settings `language`, `media` (registry, optional); `kc new-module --remote --language
  --private --media`; size limit `large_file_mb` (default 20): `kc` never commits bigger files;
  media goes to the module's media folder, large files to `<media>/large/`. (ADR 0007)
- Session drafts: raw transcript captured by `kc hook stop|pre-compact|session-end` (background,
  every 5 turns / 15 min), `kc draft`, `kc hook session-start`; adapter `transcript:` spec;
  `kc push-external NAME`. (ADR 0006)
- `ecosystem/todo/` (pending work, one file per item), `ecosystem/decisions.md`, `kc todo`
  (stubs leftover inbox/drafts files, lists items; replaces `kc check-drafts`),
  `skills/todo.md`; automatic `kc` changes are committed as `auto: …`. (ADR 0005)
- `kc update NAME` / `kc detach NAME [--yes]`; `skills/update.md` (resolve an update, adapt
  content); registry field `upstream`; AGENTS.md section *Session start*. (ADR 0003)
- AGENTS.md *Large tasks*: estimate scale, then background / now / defer. (ADR 0004)

### Removed
- `HOME.md` and `kc home` (the map is `kc registry` with the new `description` field);
  `kc check-template`. **Migration:** `kc set NAME description="…"` for each module; delete
  `ecosystem/HOME.md`. (ADR 0013)
- Engine no longer ships `ecosystem/registry.yml`, `HOME.md`, `decisions.md`, `templates.yml`;
  `kc bootstrap` creates the state files; default catalog moved to `config/templates.yml`
  (https URL). **Migration:** none for existing cores — files you already have stay; your own
  catalog entries stay in `ecosystem/templates.yml`. (ADR 0009)
- `kc index`, `kc lint`, `kc check`, `kc compact-log`, `skills/compact-log.md`, `kc push-external`:
  format tools now ship with templates (`tools/notes.py` in the info template); `kc` never
  commits in external modules. **Migration:** add `check: python tools/notes.py check` to
  registry entries of info-template modules after they absorb the template update. (ADR 0008)
- `ecosystem/log.md`, `ecosystem/journal.md`, `ecosystem/candidates.md`, `kc check-drafts`.
  **Migration:** move open candidates to todo items (`kind: candidate`); keep old log/journal
  content in git history or fold key decisions into `decisions.md`. (ADR 0005)

### Changed
- `close` asks the human about every discrepancy with recorded knowledge; reusable artifacts
  are assessed when created; moving a module onto a new template is described. (ADR 0013)
- subprocess output is decoded as UTF-8 (Cyrillic paths and messages on Windows).
- Every commit is pushed right away (`kc commit-push`, `auto:` commits); confirmation only for
  external modules and template/engine proposals. `--push` flag removed. Claude adapter hooks
  replaced; kc-owned hook entries are replaced, not duplicated. **Migration:** run
  `kc ensure-wrappers --agent claude`. (ADR 0006)
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
