"""Command-line interface for the repo-local scix workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bootstrap import doctor, install_missing_repos, perform_up, up_guidance
from .cheatsheet import render_cheat_sheet_text
from .exceptions import CheckFailedError, ScixError
from .generator import find_workspace_root, sync_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scix")
    subparsers = parser.add_subparsers(dest="command", required=True)

    up_parser = subparsers.add_parser(
        "up",
        help="Generate workspace files, clone configured repos, and check agent tooling",
    )
    up_parser.add_argument(
        "--skip-repos",
        action="store_true",
        help="Skip cloning reference repositories",
    )
    up_parser.add_argument(
        "--check",
        action="store_true",
        help="Run doctor at the end and fail on issues",
    )
    up_parser.set_defaults(func=cmd_up)

    sync_parser = subparsers.add_parser(
        "sync",
        help="Regenerate generated files from repos.yaml and ai/",
    )
    sync_parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of rewriting stale files",
    )
    sync_parser.set_defaults(func=cmd_sync)

    cheat_parser = subparsers.add_parser(
        "cheat",
        help="Show curated workflow command sets for this repo",
    )
    cheat_parser.set_defaults(func=cmd_cheat)

    repo_parser = subparsers.add_parser(
        "install-repos",
        help="Clone missing reference repositories declared in repos.yaml",
    )
    repo_parser.set_defaults(func=cmd_install_repos)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Validate the current scix-hub checkout",
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    return parser


def cmd_up(args: argparse.Namespace) -> int:
    root = Path.cwd()
    changes = perform_up(
        root,
        skip_repos=args.skip_repos,
        check=args.check,
    )
    print(f"\npython -m scix up completed with {len(changes)} changed paths")
    print("\nNext steps:")
    for note in up_guidance(root):
        print(f"- {note}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    changed = sync_workspace(find_workspace_root(), check=args.check)
    if args.check:
        print("python -m scix sync --check passed")
    else:
        print(f"python -m scix sync updated {len(changed)} paths")
    return 0


def cmd_cheat(args: argparse.Namespace) -> int:
    del args
    print(render_cheat_sheet_text(), end="")
    return 0


def cmd_install_repos(args: argparse.Namespace) -> int:
    del args
    cloned = install_missing_repos(find_workspace_root())
    print(f"Installed {len(cloned)} repositories")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    del args
    report = doctor(find_workspace_root())
    if report:
        for line in report:
            print(line)
        return 1
    print("python -m scix doctor passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CheckFailedError as exc:
        print(str(exc))
        return 1
    except ScixError as exc:
        print(str(exc))
        return 1
