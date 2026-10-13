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
2. Read the start report (`kc sync:` and `kc signals:`). Order: a `FAIL:` on the core first (the
   todo poll waits until the core is clean); then the todo poll (see Todo below); then, in one
   short message, before the human's request takes over:
   - Every `FAIL:` line (a conflict, not pushed, fetch failed, wrong branch, unreadable registry…)
     — say which repo and what it means, and offer to fix it now. Do not write to a repo with an
     unresolved conflict. To resolve a conflict: `git -C <repo> pull --rebase origin main`, edit
     each conflicted file keeping both sides' content where both matter (ask the human when they
     contradict), `git add` it, `git -C <repo> rebase --continue`, then `kc sync`. **Never**
     `git reset --hard`, `git push --force`, `git clean` or delete commits: kc keeps local commits
     safe, and these would lose them. **Which side is which:** the `kc sync` report names this
     device's commit and the other device(s)' commit. Inside the conflict markers of a
     `pull --rebase` it is reversed: `<<<<<<< HEAD` is **origin = the other device(s)**, and the
     side marked `>>>>>>> <sha> (<message>)` is **this device**. Check with `git -C <repo> log -1
     origin/main` before showing the human which decision came from where.
     **`ecosystem/registry.yml`** (and any YAML): never keep both copies of a key — merge each
     module's fields into one entry. A conflict on `template_version`, or on a file a template
     owns in a module: keep either side — except that a module's **own edit** of such a file is
     kept (ask the human when both sides edited it) — finish the sync, then run
     `kc template-update T`: it recognises files that are just behind the template and brings
     them to its current version.
   - `committed leftovers (files…)` — a previous session ended without committing. Tell the human
     which files were committed and check them with `git -C <repo> show --stat HEAD` if unsure.
   - `in the registry but not set up on this device: …` — mention it once. If the human needs one
     of them here: `python -m kc attach NAME [--path P]`.
   - `format:` — fix mechanical problems yourself right away (run the module's check with `-v`,
     fix, commit); show content problems to the human.
   - `structure:` — the module grew: look at it and propose what to do (split, new module, a
     process), or say it is fine; then run `kc reviewed NAME`.
   - `repeat:` — a manual procedure reached 3 times: propose to make it a process (below).
   - `template:` — a template is ahead of its modules: show `kc template-update T --dry-run`
     and run it on the human's yes; carry over what it lists as not owned (`AGENTS.md`…) by hand,
     and bring in "KEPT LOCAL" files with the human. A KEPT LOCAL file merged by hand together
     with the module's own edits keeps showing up: once merged, record it with
     `kc template-bind NAME T --version SHA` (SHA = the template commit you merged from).
   - `todo` rows — handled by the Todo rules below. `open:` (Candidates, or an unknown section)
     — mention the count.
   If the human is in a hurry, add what you did not raise to `ecosystem/todo.md` and move on —
   except what they already cancelled in the poll (in the poll, "the next session" is the hurry
   answer). Only the human says they are in a hurry: never skip or postpone the poll or this
   report on your own judgment (late hour, an urgent-looking request) — ask the questions and
   let them pick "the next session". *Why:* a session that skipped the poll on its own left
   agreed items unasked.
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
  module, in the module's language — as two separate commands, `git -C <module> add -A` then
  `git -C <module> commit -m "…"` (single commands are pre-approved; `cd … &&` chains are not).
  Run a module's tools the same way, from anywhere: `python <module>/tools/notes.py index` /
  `check` — never edit a generated file (`index.md`) by hand. On Windows use the Bash tool for
  git, kc and module tools (the allow-list covers them there).
- **A module still showing template placeholders** (`setup:` signal, or `> Replace …` in its
  `AGENTS.md`): before the first write into it, ask what it is for and rewrite them. The end hook pushes it and
  commits anything you left (as `auto: sync`). Run `kc sync` yourself when the human switches
  devices or asks.
- Never write into a `frozen` or `external` module, and never commit one.
- **A domain whose module is not on this device is off-limits.** Its rules live in that module
  (e.g. calendar rules in a planning module): without them, don't act in that domain — and don't
  use external tools that write there (a calendar, a mailbox). Offer `kc attach NAME` instead.

## Todo

`ecosystem/todo.md`: sections **Discuss** (to discuss with the human), **Dated** (date-bound),
**Tech** (system chores you do yourself) — the headings may be in Russian (Обсудить / Сроки /
Техническое); one line per item, fields first, text in the core's language (format at the top of
the file). `due` = by this date, `after` = not before, `when` = the day agreed with the human,
`module`, `device` (`mac`, `windows` or `linux`), `confirm: yes` (a tech item that is
irreversible or changes the system), `postponed: N`. A new item goes to Tech if only you act on
it, to Dated if a date drives it, else to Discuss.

- **The poll** — at session start, after a core `FAIL:` is resolved and before the human's
  request: ask about every row kc marks to ask (not `today`, not plain `tech`), with
  AskUserQuestion (up to 4 questions per call; several calls if needed). Options: now / a
  concrete time / the next session / already done / cancel. Record each answer at once:
  - a time → `when:` that date (replace an old `when`, never add a second). Propose the slot by
    the scheduling rules `ecosystem/rules.md` points to (e.g. a planning module's calendar
    rules); with none, or without access to the calendar, ask for a date. Never after the
    item's `due`;
  - the next session → add 1 to `postponed` (start at 1) and drop a passed `when`; the item is
    asked again at every session — by design. At `postponed` 5+ kc says so: offer a date or
    cancel;
  - already done / now (then do it) / cancel → delete the line.
  No answer = the next session.
- **`today`** (its `when` is today): planned for today — remind the human in the short report,
  don't ask. **Missed** (its `when` has passed): ask again like any other item.
- **Tech items**: do plain ones yourself when the session has room, and report. A tech item with
  `confirm: yes` goes into the poll as "may I do it now?". Mark `confirm: yes` when adding an item
  that is irreversible (deleting, archiving, revoking) or changes how the system works.
- **Flags** kc may print instead of a label: `bad date`, `bad device`, `fix the line` (a field
  twice, a field in Russian, a bad `postponed`), `after … is later than due`, `agreed … after its
  due` / `before its after`, `dated, but no date`, `unclosed … hides the lines below it`. Fix the
  line yourself if the intent is clear, else ask.
- **A new item mid-session**: add it with its fields at once; if it needs the human, ask right
  away when to take it up, proposing a slot. An item done mid-session: delete its line.
- **After editing todo.md**: commit and push the core at once (`kc sync`), so the other device
  sees it.
- **A conflict in todo.md** (kc refuses to read it): resolve it by item, with
  `git -C <core> config merge.conflictStyle zdiff3` set so the base version shows. A line
  deleted on one side and untouched on the other stays deleted (done or cancelled); both sides
  added items → keep both; both changed the same item differently → ask the human. Never keep
  both versions of one item.
- **Calendar** (if the human keeps one): add an agenda to the description of an existing block
  only after asking the human each time; never create events for todo items without them. There
  is no fixed weekly discussion block — each item gets its own slot.
- The day is taken in `timezone` of `ecosystem/instance.yml`, at session start.

## Running a module's process

A process is a module's skill, `.claude/skills/<name>/SKILL.md`; `kc registry` lists them.
When the human asks for something a process covers ("let's study"), read that SKILL.md and
follow it, working inside that module. The same skill works when the module is opened alone.

Creating or editing a process writes into the module's `.claude/` folder, which Claude Code
protects: the human must approve that write when Claude Code asks. Say so before you write, so
the prompt is expected. If the write cannot be approved (e.g. a non-interactive session), give
the file's full text and its path for the human to save.

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

- Before proposing any change to how this system works (the core, kc, hooks, templates, the way
  modules are cut), read `ecosystem/history.md` if the core keeps one: the problems already met
  and the lessons from them.

- New module: propose name, description, template (`kc templates`), private or not, and a
  remote (an empty repo the human creates; private for personal content). Then
  `kc new-module NAME --template T --remote URL [--private] --description "…"`, replace the
  template's placeholders with the module's real purpose, and record the decision in
  `ecosystem/decisions.md`.
- Changing a template (its skills, assets, tools): in its local clone, on `main` after a pull, edit, commit, push, then
  `kc template-update` (see `docs/templates.md`). Never copy template files into modules by hand.
- Moving content between modules: re-write it in the target module's format, then delete it
  from the source — never link across modules.
- Retire: `kc set NAME status=frozen` (read-only, kept). Record why in `decisions.md`.

## Memory

`ecosystem/rules.md` holds the human's own rules for you that hold only in this setup (which
module plans and keeps the calendar, how the engine is published…); `CLAUDE.md` loads it after
this file, and it wins where it is more specific.

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
- Anything you leave for later ("update at the next review") goes into `ecosystem/todo.md`,
  with its dates and module as fields (see Todo) — a promise that lives only in a note is lost.
- Dates: compute weekdays with a tool before writing them (`python -c "import datetime; …"`);
  never guess "Thursday 09.10".
