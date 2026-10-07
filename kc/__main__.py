"""kc — the core's orchestrator: the registry of modules and git across them (ADR 0015).

kc knows which repos exist and keeps them in sync; it never decides what to write or where.
Run it from the core root: `python3 -m kc …` (on Windows: `python -m kc …`).

  kc bootstrap [--device-id ID] [--language L] [--yes]   set up this device (re-runnable)
  kc registry                     the map: modules, flags, paths, descriptions, processes
  kc templates                    the module-template catalog
  kc new-module NAME (--template T | --template-url URL | --no-template)
                 [--path P] [--remote URL] [--private] [--description TEXT]
  kc add-module NAME PATH [--external] [--private] [--description TEXT] [--check CMD]
  kc set NAME key=value ...       description, remote, status (active|frozen), private, check
  kc reviewed NAME                mark a module's structure as reviewed (resets the signal)
  kc sync [-m MSG]                commit leftovers, pull, push: the core + modules on this device
  kc status                       local state of every repo + maintenance signals (no network)
  kc hook start|end               Claude Code hooks: start = sync + signals, end = sync
"""
import argparse
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from . import core as C  # noqa: E402


def _parser():
    p = argparse.ArgumentParser(prog="kc", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")

    b = sub.add_parser("bootstrap", help="set up this device")
    b.add_argument("--device-id")
    b.add_argument("--language")
    b.add_argument("--yes", action="store_true", help="accept defaults, ask nothing")

    sub.add_parser("registry", help="the map of modules")
    sub.add_parser("templates", help="the module-template catalog")

    n = sub.add_parser("new-module", help="create a module")
    n.add_argument("name")
    g = n.add_mutually_exclusive_group(required=True)
    g.add_argument("--template")
    g.add_argument("--template-url")
    g.add_argument("--no-template", action="store_true")
    n.add_argument("--path")
    n.add_argument("--remote")
    n.add_argument("--private", action="store_true")
    n.add_argument("--description")

    a = sub.add_parser("add-module", help="register an existing repo")
    a.add_argument("name")
    a.add_argument("path")
    a.add_argument("--external", action="store_true", help="not yours: read only, never committed")
    a.add_argument("--private", action="store_true")
    a.add_argument("--description")
    a.add_argument("--check")

    s = sub.add_parser("set", help="change registry fields")
    s.add_argument("name")
    s.add_argument("pairs", nargs="+", metavar="key=value")

    r = sub.add_parser("reviewed", help="mark a module's structure as reviewed")
    r.add_argument("name")

    y = sub.add_parser("sync", help="commit leftovers, pull, push")
    y.add_argument("-m", "--message")

    sub.add_parser("status", help="local state + signals")

    h = sub.add_parser("hook", help="assistant hook entry")
    h.add_argument("event", choices=["start", "end"])
    return p


def main(argv):
    p = _parser()
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    core = C.find_core()
    if not core:
        raise SystemExit("kc: no core here — run kc from the core (or set KC_CORE)")
    if args.cmd == "bootstrap":
        from . import bootstrap
        return bootstrap.run(core, args.device_id, args.language, args.yes)
    if args.cmd == "registry":
        from . import registry
        return registry.show(core)
    if args.cmd == "templates":
        from . import modules
        return modules.show_templates(core)
    if args.cmd == "new-module":
        from . import modules
        return modules.new_module(core, args.name, args.template, args.template_url, args.no_template,
                                  args.path, args.remote, args.private, args.description)
    if args.cmd == "add-module":
        from . import modules
        return modules.add_module(core, args.name, args.path, args.external, args.private,
                                  args.description, args.check)
    if args.cmd == "set":
        from . import registry
        return registry.set_fields(core, args.name, args.pairs)
    if args.cmd == "reviewed":
        from . import registry
        return registry.mark_reviewed(core, args.name)
    from . import sync
    if args.cmd == "sync":
        return sync.cmd_sync(core, args.message)
    if args.cmd == "status":
        return sync.cmd_status(core)
    if args.cmd == "hook":
        return sync.hook(core, args.event)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
