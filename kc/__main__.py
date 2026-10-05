"""kc — mechanical maintenance CLI for a knowledge-core ecosystem.

Deterministic, model-agnostic plumbing that any agent or git hook can call.
The cognitive work (what to write, where, reconciling) lives in skills/ and is done
by an assistant; kc only does the deterministic parts the skills invoke.

Module-scoped (run in any module):
  kc index [DIR]              regenerate DIR/index.md
  kc lint  [DIR] [-v]         frontmatter + broken intra-module [[links]] + index freshness
  kc check [DIR]              index + lint -v

Center-scoped (finds the center via KC_CENTER or by searching upward):
  kc registry                show resolved modules on this device
  kc pull-all                pull center + present modules (fork model; external = ff)
  kc commit-push [--all] [--push] -m MSG   commit current module (or --all); push only with --push
  kc push-all                push center + present modules that have unpushed commits
  kc check-drafts            report pending inbox/ and drafts/
  kc ensure-wrappers --agent NAME   regenerate NAME's command wrappers from the canon
  kc add-agent NAME          install an assistant's wrappers + startup stub

DIR defaults to the current directory.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from . import maintain, repos          # noqa: E402
from . import center as C              # noqa: E402


def _need_center():
    c = C.find_center()
    if not c:
        raise SystemExit("kc: no center found (set KC_CENTER or run inside one)")
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

    if cmd == "index":
        maintain.cmd_index(Path(rest[0]).resolve() if rest else Path.cwd())
    elif cmd == "lint":
        maintain.lint(Path(rest[0]).resolve() if rest else Path.cwd(), verbose)
    elif cmd == "check":
        root = Path(rest[0]).resolve() if rest else Path.cwd()
        maintain.cmd_index(root)
        maintain.lint(root, True)
    elif cmd == "registry":
        repos.show_registry(_need_center())
    elif cmd == "pull-all":
        repos.pull_all(_need_center())
    elif cmd == "commit-push":
        all_repos = "--all" in rest
        do_push = "--push" in rest
        rest = [a for a in rest if a not in ("--all", "--push")]
        msg = None
        if "-m" in rest:
            i = rest.index("-m")
            msg = rest[i + 1] if i + 1 < len(rest) else None
        if not msg:
            raise SystemExit("kc commit-push: -m MSG required")
        repos.commit_push(_need_center(), msg, all_repos=all_repos, do_push=do_push)
    elif cmd == "push-all":
        repos.push_all(_need_center())
    elif cmd == "check-drafts":
        return repos.check_drafts(_need_center())
    elif cmd == "ensure-wrappers":
        agent = _opt(rest, "--agent")
        if not agent:
            raise SystemExit("kc ensure-wrappers: --agent NAME required")
        from . import wrappers
        wrappers.ensure_wrappers(_need_center(), agent)
    elif cmd == "add-agent":
        if not rest:
            raise SystemExit("kc add-agent: NAME required")
        from . import wrappers
        wrappers.add_agent(_need_center(), rest[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
