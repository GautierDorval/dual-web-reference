"""Command-line interface. Network-free commands: verify, analyze, render, build-site,
project-public, revise-public, qualify, normalize, status, prepare-edition, prepare-next,
import-existing, publication-gate.
acquire-readonly is the only command able to contact the producer database; it is
a dry run unless --execute and an exact --confirm-scope are given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .common import DwrError, REPO_ROOT, private_root


def _print(value) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dwr", description="Dual Web Reference calculation chain")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text, private=False):
        command = sub.add_parser(name, help=help_text)
        if private:
            command.add_argument("--private-root", default=None,
                                 help="private workspace outside this repository (or DWR_PRIVATE_ROOT)")
        command.add_argument("--edition", default=None, help="edition identifier (default: candidate edition)")
        return command

    command = add("import-existing", "verify a local export package and load its marginals", private=True)
    command.add_argument("--package", required=True)
    command = add("acquire-readonly", "bounded read-only SELECT extraction (dry run by default)", private=True)
    command.add_argument("--execute", action="store_true")
    command.add_argument("--confirm-scope", default=None)
    command = add("prepare-next", "prepare the next consolidated window privately, offline", private=True)
    add("normalize", "typed working representation (private)", private=True)
    add("qualify", "apply scope, attribution and coverage rules (private)", private=True)
    add("project-public", "write the minimized public projection of an edition", private=True)
    add("revise-public", "prepare a local privacy revision from frozen public observations")
    add("analyze", "recompute metrics.json from the public projection only")
    add("render", "figures, generated README/doc blocks from public data")
    add("verify", "replay all offline checks")
    add("build-site", "build the static presentation into site/dist")
    add("prepare-edition", "candidate package, digests and delta report")
    add("status", "data, edition and preparation state")
    command = add("publication-gate", "check every Git object of the branch to publish (private values never printed)",
                  private=True)
    command.add_argument("--ref", default="public-candidate", help="branch or commit to publish")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except DwrError as error:
        sys.stderr.write(f"FAIL {error.code}: {error.detail}\n")
        return 2


def _dispatch(args) -> int:
    from . import pipeline

    command = args.command
    if command == "prepare-next":
        from . import maintenance
        result = maintenance.prepare(private_root(args.private_root))
        _print(result)
        return 1 if result["outcome"] in ("validation_failed", "source_unavailable") else 0
    elif command == "import-existing":
        _print(pipeline.cmd_import(Path(args.package), private_root(args.private_root), args.edition))
    elif command == "acquire-readonly":
        _print(pipeline.cmd_acquire(private_root(args.private_root) if args.execute else None,
                                    args.edition, args.execute, args.confirm_scope))
    elif command == "revise-public":
        from . import revisions
        _print(revisions.prepare(args.edition))
    elif command == "publication-gate":
        from . import gate
        from .common import REPO_ROOT
        result = gate.check_ref(REPO_ROOT, args.ref, gate.load_secrets(private_root(args.private_root)))
        _print(result)
        return 0 if result["passed"] else 1
    elif command in ("normalize", "qualify", "project-public"):
        _print(getattr(pipeline, "cmd_" + command.replace("-", "_"))(private_root(args.private_root), args.edition))
    elif command in ("analyze", "render", "verify", "build-site", "prepare-edition", "status"):
        result = getattr(pipeline, "cmd_" + command.replace("-", "_"))(args.edition)
        _print(result)
        if command == "verify" and not result.get("passed"):
            return 1
    return 0
