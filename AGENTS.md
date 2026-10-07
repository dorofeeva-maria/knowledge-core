# knowledge-core — agent instructions

You work from the **core**: the orchestrator of the human's modules. Each module is its own git
repo with its own subject, rules (`AGENTS.md`), processes (`.claude/skills/`) and format tools.
The core holds no subject knowledge — only the map of modules and a few state files.

Who does what (ADR 0015):

- **`kc`** (`python3 -m kc …` from the core root; on Windows `python -m kc …`) — the registry
  and git across all repos. It never decides what to write or where.
- **Hooks** — sync every repo at session start and end; the start hook also reports signals.
- **You** — capture what the conversation decides into the right module, at once; keep modules
  consistent; raise maintenance the moment you see it.
- **The human** — decides structure (new module, split, freeze), resolves content conflicts.

## Session start

1. Read `ecosystem/memory.md`: facts about the human that hold everywhere.
2. Read the start report (`kc sync:` and `kc signals:`). Then, in one short message, before the
   human's request takes over:
   - Every `FAIL:` line (a conflict, not pushed, fetch failed, wrong branch, unreadable registry…)
     — say which repo and what it means, and offer to fix it now. Do not write to a repo with an
     unresolved conflict. To resolve a conflict: `git -C <repo> pull --rebase origin main`, edit
     each conflicted file keeping both sides' content where both matter (ask the human when they
     contradict), `git add` it, `git -C <repo> rebase --continue`, then `kc sync`. **Never**
     `git reset --hard`, `git push --force`, `git clean` or delete commits: kc keeps local commits
     safe, and these would lose them.
   - `format:` — fix mechanical problems yourself right away (run the module's check with `-v`,
     fix, commit); show content problems to the human.
   - `structure:` — the module grew: look at it and propose what to do (split, new module, a
     process), or say it is fine; then run `kc reviewed NAME`.
   - `repeat:` — a manual procedure reached 3 times: propose to make it a process (below).
   - `todo open:` — mention the count; walk through `ecosystem/todo.md` only if the human wants.
   If the human is in a hurry, add what you did not raise to `ecosystem/todo.md` and move on.
3. `kc registry` is the map: each module's description, path on this device, flags and
   processes. Run it whenever you need to choose a module.

## Writing knowledge — at once, not at the end

There is no "close" step: whatever is not written during the session is lost.

- The moment something is decided, learned or changed in the conversation — a fact, a decision,
  a plan update, a preference — write it into the module it belongs to. Do not wait to be asked.
- Pick the module by its registry description. If nothing fits, say so and propose a new module
  (record it under `## Candidates` in `ecosystem/todo.md` if the human defers); do not invent one
  silently, and do not park subject knowledge in the core. Core files (`todo.md`,
  `decisions.md`, `memory.md`) hold short pointers, never the content itself — least of all
  confidential work material.
- Follow the module's `AGENTS.md` (format, language, folders, links). Prefer updating an
  existing note over creating a near-duplicate.
- **Reconcile while writing.** If the new information contradicts what the module already says,
  show both versions (with dates) and ask the human which holds. Keep the old value with its
  period ("until 2026-10: …") when history matters.
- **Files.** A file to keep reaches you as a path (the human drags it into the terminal). Copy it
  into the module's media folder (per its `AGENTS.md`; `media/` if it names none) and link it
  from the note. If the file's folder is outside what you may access, ask the human to allow it
  (in Claude Code: `/add-dir <folder>`) or to copy the file in. A pasted image is not saved as a
  file — ask for the path if it should be kept. Large or device-only files go into the module's
  own `.gitignore`.
- **Commit with meaning.** After writing into a module, commit there with a message about that
  module, in the module's language: `git -C <module> add -A && git -C <module> commit -m "…"`. The end hook pushes it and
  commits anything you left (as `auto: sync`). Run `kc sync` yourself when the human switches
  devices or asks.
- Never write into a `frozen` or `external` module, and never commit one.

## Running a module's process

A process is a module's skill, `.claude/skills/<name>/SKILL.md`; `kc registry` lists them.
When the human asks for something a process covers ("let's study"), read that SKILL.md and
follow it, working inside that module. The same skill works when the module is opened alone.

## Maintenance you start yourself

The human will not run maintenance on request; noticing it is your job.

- **Growth.** When a module or a theme in it grows tangled, a cluster forms that has its own
  goal, process or rhythm, or a note grows too big — say so right then and propose: split the
  note, move the cluster into a new module, make a process. Record it under `## Candidates` in
  `ecosystem/todo.md` if the human defers.
- **Repeats.** When you do a multi-step, subject-specific procedure by hand (e.g. "build a deck
  from today's words"), add or bump its line under `## Repeats` in `ecosystem/todo.md`:
  `- 2× · what was done · module · last YYYY-MM-DD`. At 3× propose turning it into a process.
- **Before creating a script, skill or module**, say why it is needed now and what it replaces.

## Structure changes (the human decides)

- New module: propose name, description, template (`kc templates`), private or not, and a
  remote (an empty repo the human creates; private for personal content). Then
  `kc new-module NAME --template T --remote URL [--private] --description "…"`, replace the
  template's placeholders with the module's real purpose, and record the decision in
  `ecosystem/decisions.md`.
- Moving content between modules: re-write it in the target module's format, then delete it
  from the source — never link across modules.
- Retire: `kc set NAME status=frozen` (read-only, kept). Record why in `decisions.md`.

## Memory

`ecosystem/memory.md` holds only what is true across all modules: lasting facts about the human
and how to work with them (one bullet: the fact, then **Why:**). Subject facts — a medication
dose, a score, a plan — belong in a module, even if that module does not exist yet (then a
candidate). A rule for one module goes into that module's `AGENTS.md`. Each rule lives in one
place: never write the same rule into both.

**A new statement that contradicts a memory bullet is confirmed first**: show the recorded
version (with its **Why:**) and the new one, and change the bullet only after the human
confirms — especially when the bullet says it was corrected before. Your assistant's built-in
memory is off in the core.

## Ground rules

- Modules know nothing of the core or of each other: no links between modules, no mention of
  the core inside a module. Related notes in different modules share tags in their frontmatter
  (people, places, stack, `private`); find them with grep across module paths.
- Privacy: details of a `private` module or a `private`-tagged note never go into another module
  or anything public — mention them only in general terms. Personal material goes only into a
  private module.
- External modules (not the human's, e.g. a work repo) are read only.
- Large tasks (many files, several modules): state the scale first and let the human choose
  now / in the background / later (ADR 0004).
- When what you find disagrees with what is recorded (registry, a note, memory), ask.
