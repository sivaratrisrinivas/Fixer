"""Command line entry point: ``python -m fixer "fix the failing test" --dir path``."""

from __future__ import annotations

import argparse
import sys
from typing import Any, TextIO

from .agent import Reply, run_agent
from .tools import Toolbox, ToolResult
from .workspace import Workspace


def make_approver(auto_yes: bool, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout):
    def approve(path: str, diff: str) -> bool:
        print(f"\nFixer wants to change {path}:\n{diff}", file=stdout)
        if auto_yes:
            print("(approved by --yes)", file=stdout)
            return True
        if not stdin.isatty():
            print("Refused: no terminal to confirm on. Re-run with --yes to allow writes.", file=stdout)
            return False
        stdout.write("Apply this change? [y/N] ")
        stdout.flush()
        return stdin.readline().strip().lower() in {"y", "yes"}

    return approve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fixer", description="A small coding agent that works inside one directory.")
    parser.add_argument("prompt", nargs="+", help="What you want done")
    parser.add_argument("--dir", default=".", help="Project directory the agent may touch (default: current)")
    parser.add_argument("--model", default=None, help="Gemini model (default: $FIXER_MODEL or gemini-2.5-flash)")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--yes", action="store_true", help="Apply file changes without asking")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    from .gemini import GeminiModel

    try:
        model = GeminiModel(model=args.model)
    except RuntimeError as exc:
        print(f"Error: {exc}. Put it in .env or the environment.", file=sys.stderr)
        return 2

    toolbox = Toolbox(Workspace(args.dir), make_approver(args.yes))

    def on_event(kind: str, payload: Any) -> None:
        if kind == "tool":
            assert isinstance(payload, ToolResult)
            print(f"-> {payload.name}({payload.args})")
            if args.verbose:
                print(payload.output)
        elif kind == "model" and args.verbose:
            assert isinstance(payload, Reply)
            if payload.usage:
                print(f"   tokens: {payload.usage}")

    result = run_agent(model, toolbox, " ".join(args.prompt), max_steps=args.max_steps, on_event=on_event)
    print("\n" + result.answer)
    if result.writes:
        print(f"\nFiles changed: {', '.join(result.writes)}")
    return 0 if result.finished else 1
