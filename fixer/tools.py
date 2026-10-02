"""The agent's tools. Each one returns a string the model can read.

Tools never raise for expected problems (missing file, path outside the
workspace, a rejected write). They return an ``Error: ...`` string instead, so
the model can recover in the next step.
"""

from __future__ import annotations

import difflib
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .workspace import OutsideWorkspace, Workspace

MAX_READ_CHARS = 10_000
MAX_OUTPUT_CHARS = 8_000
RUN_TIMEOUT_S = 30
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}

# approve(path, diff) -> True to write, False to refuse.
Approver = Callable[[str, str], bool]


def _clip(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... truncated {len(text) - limit} characters]"


def _child_env() -> dict[str, str]:
    """Environment for code the agent runs: no API keys, no inherited secrets."""
    keep = {"PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH", "SYSTEMROOT", "TMPDIR"}
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


@dataclass
class ToolResult:
    name: str
    args: dict[str, Any]
    output: str


@dataclass
class Toolbox:
    workspace: Workspace
    approve: Approver
    writes: list[str] = field(default_factory=list)

    # Tool specs in a provider-neutral JSON-schema shape. Model adapters translate these.
    SPECS: ClassVar[tuple[dict[str, Any], ...]] = (
        {
            "name": "list_files",
            "description": "List files and folders in a directory of the workspace with their sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Relative directory. Defaults to the workspace root."}
                },
            },
        },
        {
            "name": "read_file",
            "description": "Read a text file from the workspace (first 10,000 characters).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path."}},
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Create or overwrite a file. The user sees a diff and must approve it before it is written.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "The full new file content."},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "run_python",
            "description": "Run a Python file in the workspace with optional arguments (30 second limit).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to a .py file."},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command line arguments."},
                },
                "required": ["path"],
            },
        },
        {
            "name": "run_tests",
            "description": "Run the project's tests (pytest if present, otherwise unittest discovery) and report the result.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Optional test file or directory, relative."}},
            },
        },
    )

    def call(self, name: str, args: dict[str, Any] | None) -> ToolResult:
        args = dict(args or {})
        handler = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_python": self.run_python,
            "run_tests": self.run_tests,
        }.get(name)
        if handler is None:
            return ToolResult(name, args, f'Error: unknown tool "{name}"')
        try:
            output = handler(**args)
        except OutsideWorkspace as exc:
            output = f"Error: {exc}"
        except TypeError as exc:
            output = f"Error: bad arguments for {name}: {exc}"
        return ToolResult(name, args, output)

    def list_files(self, directory: str | None = None) -> str:
        target = self.workspace.resolve(directory)
        if not target.is_dir():
            return f'Error: "{directory}" is not a directory'
        lines = []
        for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
            if entry.name in SKIP_DIRS:
                continue
            kind = "dir" if entry.is_dir() else f"{entry.stat().st_size} bytes"
            lines.append(f"- {self.workspace.relative(entry)}{'/' if entry.is_dir() else ''} ({kind})")
        return "\n".join(lines) or "(empty directory)"

    def read_file(self, path: str) -> str:
        target = self.workspace.resolve(path)
        if not target.is_file():
            return f'Error: file not found: "{path}"'
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f'Error: "{path}" is not a UTF-8 text file'
        if len(text) > MAX_READ_CHARS:
            return text[:MAX_READ_CHARS] + f'\n[... "{path}" truncated at {MAX_READ_CHARS} characters]'
        return text

    def write_file(self, path: str, content: str) -> str:
        target = self.workspace.resolve(path)
        if target.is_dir():
            return f'Error: "{path}" is a directory'
        old = target.read_text(encoding="utf-8") if target.is_file() else ""
        if old == content:
            return f'No change: "{path}" already has that content'
        rel = self.workspace.relative(target)
        diff = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{rel}" if old else "/dev/null",
                tofile=f"b/{rel}",
            )
        )
        if not self.approve(rel, diff):
            return f'Error: the user rejected the change to "{rel}". Ask what they want instead, or try a different fix.'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.writes.append(rel)
        return f'Wrote "{rel}" ({len(content)} characters).\n{_clip(diff, 2_000)}'

    def _run(self, cmd: list[str]) -> str:
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace.root,
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_S,
                env=_child_env(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return f"Error: timed out after {RUN_TIMEOUT_S} seconds"
        parts = [f"exit code {proc.returncode}"]
        if proc.stdout:
            parts.append("STDOUT:\n" + proc.stdout)
        if proc.stderr:
            parts.append("STDERR:\n" + proc.stderr)
        return _clip("\n".join(parts))

    def run_python(self, path: str, args: list[str] | None = None) -> str:
        target = self.workspace.resolve(path)
        if target.suffix != ".py":
            return f'Error: "{path}" is not a Python file'
        if not target.is_file():
            return f'Error: file not found: "{path}"'
        return self._run([sys.executable, str(target), *[str(a) for a in (args or [])]])

    def run_tests(self, path: str | None = None) -> str:
        target = self.workspace.resolve(path)
        rel = self.workspace.relative(target)
        try:
            import pytest  # noqa: F401

            cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", rel]
        except ImportError:
            if target.is_file():
                cmd = [sys.executable, "-m", "unittest", "-v", rel.removesuffix(".py").replace("/", ".")]
            else:
                cmd = [sys.executable, "-m", "unittest", "discover", "-v", "-s", rel, "-p", "*test*.py"]
        return self._run(cmd)
