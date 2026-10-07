# Architecture

knowledge-core is an engine for a personal ecosystem of **modules** — independent git repos of
knowledge or of processes — coordinated by one orchestrator, the **core**. The input is a
conversation with Claude Code; the output is well-kept modules on every device you use.

It is built for one person on a few devices, with Claude Code as the assistant. The decisions
behind this shape are in [ADR 0015](adr/0015-simplified-architecture.md).

## Pieces and responsibilities

| Piece | Responsible for | Not responsible for |
|---|---|---|
| **Engine** (this public repo) | a starting point you copy into your core | updating cores after that |
| **Core** (your private copy) | the map of modules (`registry.yml`), the agent's rules (`AGENTS.md`), facts about you (`memory.md`), deferred work (`todo.md`), ecosystem decisions | subject knowledge |
| **Module** (a repo) | its subject: content, its own rules (`AGENTS.md`), its processes (`.claude/skills/`), its format tools and `.gitignore` | knowing about the core or other modules |
| **Template** (a repo) | the starting files of a kind of module | updating modules after they are created |
| **`kc`** | the registry, git across all repos, creating modules, setting up a device, maintenance signals | what to write and where |
| **Start hook** | `kc sync` + a report of conflicts and signals | creating work, rewriting history |
| **End hook** | `kc sync`: commit and push whatever changed | — |
| **Agent** | writing what the conversation decides into the right module at once; reconciling; raising maintenance | structural changes without the human |
| **Human** | structure, content conflicts, creating remotes | — |

## Processes

| Process | Step | Owner |
|---|---|---|
| New device | clone the core and modules, record paths, check privacy, install hooks, grant Claude access to module folders | `kc bootstrap` |
| Session start | commit leftovers, pull and push every repo | start hook → `kc sync` |
| | run module checks, compute signals | start hook → `kc` |
| | read memory and the report; fix mechanics; raise what is due | agent |
| Capture | notice what was decided; pick the module (registry); write in its format; reconcile | agent |
| | a contradiction with what is recorded | human |
| | commit with a meaningful message | agent |
| Keep a file | pass its path; copy into the module's media | human → agent |
| Run a process | find the module's skill via the registry; follow it | agent |
| Structure | notice growth and repeats; propose | agent + signals |
| | decide | human |
| | create a module | `kc new-module` |
| Session end | commit and push everything | end hook → `kc sync` |

## Sync

Each repo you own has one branch, `main`, and one remote, `origin` (shared by your devices).
`kc sync` per repo: commit uncommitted changes (`auto: sync from <device>`) → fetch → rebase your
local commits onto `origin/main` → push. History is never rewritten after it is pushed, so there
is no force-push. A conflict stops only that repo: the rebase is aborted, your commits stay
local, and the start report tells you how to resolve it.

The end hook may not run (a killed terminal); the next start hook commits what was left.

- **frozen** modules (yours, closed) are only fast-forwarded; local changes are reported.
- **external** modules (not yours) are fast-forwarded on their current branch when clean and
  never committed or pushed.

## Signals

kc reports cheap, unambiguous facts at session start; the agent turns them into a proposal:

- `format:` — a module's `check` command failed;
- `structure:` — a module grew by `review_after_notes` notes since its last review, or grew and
  `review_after_days` passed (`kc reviewed NAME` resets it);
- `repeat:` — a manual procedure in `todo.md` reached 3 times;
- `todo open:` — deferred items.

Everything that needs judgment — when a theme deserves its own module, when a procedure should
become a process — is the agent's, during the session (`AGENTS.md`).

## Modules

- **Independent.** A module works opened alone: `CLAUDE.md` → `AGENTS.md` describe it, its
  skills load natively. It never mentions the core or other modules.
- **No links between modules.** Notes in different modules relate through shared tags in their
  frontmatter; the agent finds them by grep. Knowledge moves between modules by being rewritten,
  never linked.
- **Processes are skills.** `.claude/skills/<name>/SKILL.md` inside the module. `kc registry`
  lists them, so the agent in the core can run them.
- **Templates are copies.** `kc new-module --template T` copies the template's files into a
  fresh repo; there is no link back.

## Privacy

A module flagged `private` holds personal content. Its remote must be a private repo — checked
once, when it gets a remote (`new-module`, `add-module`, `set remote=`) and at `bootstrap`. The
core is always private: `bootstrap` refuses a public core origin. The agent never carries
details of private content into other modules or anything public.

## Non-goals

Several users, several assistants, pushing engine or template updates into live repos,
background daemons, a GUI.
