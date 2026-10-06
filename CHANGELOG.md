# Changelog

Notable changes to the engine, newest first. Format: [Keep a Changelog](https://keepachangelog.com/);
decisions behind changes are in `docs/adr/`.

## Unreleased

### Changed
- The orchestrator fork is now called **core** (was *center*): `KC_CORE`, `kc/core.py`,
  core-scoped commands. Re-run `kc bootstrap` to regenerate launchers. (ADR 0002)
- ADRs use MADR-lite (adds *Considered options*) and are written whenever a choice changes
  structure, a contract or agent behavior; documentation layers defined in `docs/README.md`.
  (ADR 0001)
