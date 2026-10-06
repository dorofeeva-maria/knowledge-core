"""kc — mechanical maintenance CLI for a knowledge-core ecosystem.

Deterministic, model-agnostic plumbing that any agent or git hook can call.
The cognitive work (what to write, where, reconciling) lives in skills/ and is done
by an assistant; kc only does the deterministic parts the skills invoke.

Any repo:
  kc check-template [DIR]     flag ecosystem references in a template/module (must be standalone)

A module's own format tools (index, lint, log compaction) ship with its template and are run
through the registry field `check` (ADR 0008).

Core-scoped (finds the core via KC_CORE or by searching upward):
  kc bootstrap [--device-id ID] [--agent NAME]... [--language L] [--yes]   set up this device
  kc registry                show resolved modules on this device
  kc home                    regenerate ecosystem/HOME.md (the module map)
  kc templates               list the module-template catalog
  kc new-module NAME [--template T | --template-url URL | --no-template] [--path P]
                 [--remote URL] [--language L] [--private] [--media DIR|none] [--check CMD]
  kc add-module NAME PATH [--external [--write-zone P]...] [--upstream URL] [--language L]
                 [--private] [--media DIR|none] [--check CMD]   register an existing repo
  kc tags [TAG]              shared tag vocabulary: counts + unknown tags, or notes with TAG
  kc set NAME key=value...   change a module's registry fields (remote also rewires origin + pushes)
  kc pull-all                sync core + present modules: origin, then template/engine updates
  kc update NAME             apply a template/engine update interactively (NAME or "core")
  kc detach NAME [--yes]     stop following the template/engine (NAME or "core"); warns first
  kc commit-push [--all] -m MSG   commit + push the current repo (or --all); external: commit only
  kc push-all                push core + present modules (force-with-lease; see ADR 0003)
  kc draft [--session ID]    capture the session transcript into its draft now
  kc hook EVENT --agent NAME assistant hook entry: session-start | stop | pre-compact | session-end
  kc todo                    pending work: stub leftover inbox/drafts files, list all items
  kc ensure-wrappers --agent NAME   regenerate NAME's command wrappers from the canon
  kc add-agent NAME          install an assistant's wrappers + startup stub

DIR defaults to the current directory.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from . import maintain, repos          # noqa: E402,F401
from . import core as C              # noqa: E402


def _need_core():
    c = C.find_core()
    if not c:
        raise SystemExit("kc: no core found (set KC_CORE or run inside one)")
    return c


def _opt(rest, flag):
    if flag in rest:
        i = rest.index(flag)
        return rest[i + 1] if i + 1 < len(rest) else None
    return None


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    verbose = "-v" in rest
    rest = [a for a in rest if a != "-v"]

    if cmd == "check-template":
        return maintain.check_template(Path(rest[0]).resolve() if rest else Path.cwd())
    elif cmd == "bootstrap":
        agents = []
        i = 0
        while i < len(rest):
            if rest[i] == "--agent" and i + 1 < len(rest):
                agents.append(rest[i + 1])
                i += 2
            else:
                i += 1
        from . import bootstrap
        bootstrap.run(_need_core(),
                      device_id=_opt(rest, "--device-id"),
                      agents=agents or None,
                      language=_opt(rest, "--language"),
                      yes="--yes" in rest)
    elif cmd == "templates":
        from . import create
        create.show_templates(_need_core())
    elif cmd == "new-module":
        if not rest or rest[0].startswith("--"):
            raise SystemExit("kc new-module: NAME required")
        from . import create
        create.new_module(_need_core(), rest[0],
                          template=_opt(rest, "--template"),
                          template_url=_opt(rest, "--template-url"),
                          no_template="--no-template" in rest,
                          path=_opt(rest, "--path"),
                          remote=_opt(rest, "--remote"),
                          language=_opt(rest, "--language"),
                          private="--private" in rest,
                          media=_opt(rest, "--media"),
                          check=_opt(rest, "--check"))
    elif cmd == "add-module":
        if len(rest) < 2 or rest[0].startswith("--"):
            raise SystemExit("kc add-module: NAME PATH required")
        zones = [rest[i + 1] for i, a in enumerate(rest[:-1]) if a == "--write-zone"]
        from . import create
        create.add_module(_need_core(), rest[0], rest[1],
                          external="--external" in rest, write_zones=zones,
                          upstream=_opt(rest, "--upstream"), language=_opt(rest, "--language"),
                          private="--private" in rest, media=_opt(rest, "--media"),
                          check=_opt(rest, "--check"))
    elif cmd == "tags":
        from . import tags
        return tags.run(_need_core(), rest[0] if rest else None)
    elif cmd == "set":
        if len(rest) < 2:
            raise SystemExit("kc set: NAME key=value... required")
        from . import create
        create.set_fields(_need_core(), rest[0], rest[1:])
    elif cmd == "registry":
        repos.show_registry(_need_core())
    elif cmd == "home":
        repos.home(_need_core())
    elif cmd == "pull-all":
        repos.pull_all(_need_core())
    elif cmd == "commit-push":
        all_repos = "--all" in rest
        rest = [a for a in rest if a not in ("--all", "--push")]
        msg = None
        if "-m" in rest:
            i = rest.index("-m")
            msg = rest[i + 1] if i + 1 < len(rest) else None
        if not msg:
            raise SystemExit("kc commit-push: -m MSG required")
        repos.commit_push(_need_core(), msg, all_repos=all_repos)
    elif cmd == "draft":
        from . import session
        session.capture(_need_core(), sid=_opt(rest, "--session"), force=True)
    elif cmd == "hook":
        if not rest:
            raise SystemExit("kc hook: EVENT required")
        from . import session
        return session.hook(_need_core(), rest[0], _opt(rest, "--agent") or "claude")
    elif cmd == "update":
        if not rest:
            raise SystemExit("kc update: NAME required (a module name or 'core')")
        return repos.update(_need_core(), rest[0])
    elif cmd == "detach":
        if not rest or rest[0].startswith("--"):
            raise SystemExit("kc detach: NAME required (a module name or 'core')")
        return repos.detach(_need_core(), rest[0], yes="--yes" in rest)
    elif cmd == "push-all":
        repos.push_all(_need_core())
    elif cmd == "todo":
        from . import todo
        return todo.run(_need_core())
    elif cmd == "ensure-wrappers":
        agent = _opt(rest, "--agent")
        if not agent:
            raise SystemExit("kc ensure-wrappers: --agent NAME required")
        from . import wrappers
        wrappers.ensure_wrappers(_need_core(), agent)
    elif cmd == "add-agent":
        if not rest:
            raise SystemExit("kc add-agent: NAME required")
        from . import wrappers
        wrappers.add_agent(_need_core(), rest[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
