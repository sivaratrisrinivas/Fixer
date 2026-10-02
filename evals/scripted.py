"""Scripted models for offline evals. No network, fully deterministic.

They exist to prove the harness can tell a real fix from a non-fix: a harness
that scores every model 100% (or 0%) measures nothing.

- OracleModel explores, reproduces, writes the known fix, re-runs tests.
- NoopModel looks around and declares victory without changing anything.
- TamperModel "fixes" the bug by rewriting the test file to pass trivially.
"""

from __future__ import annotations

from pathlib import Path

from fixer.agent import Reply, ToolCall, Turn


class _Script:
    def __init__(self, steps: list[Reply]):
        self.steps = steps

    def step(self, transcript: list[Turn]) -> Reply:
        model_turns = sum(1 for t in transcript if t.role == "model")
        if model_turns < len(self.steps):
            return self.steps[model_turns]
        return Reply(text="Done.")


class OracleModel(_Script):
    def __init__(self, task_dir: Path):
        fixes = sorted(p for p in (task_dir / "fix").rglob("*") if p.is_file())
        writes = [
            ToolCall("write_file", {"path": p.relative_to(task_dir / "fix").as_posix(), "content": p.read_text()}) for p in fixes
        ]
        first = fixes[0].relative_to(task_dir / "fix").as_posix()
        super().__init__(
            [
                # Two independent calls in one turn: the loop must run both.
                Reply(tool_calls=[ToolCall("list_files", {}), ToolCall("read_file", {"path": first})]),
                Reply(tool_calls=[ToolCall("run_tests", {})]),
                Reply(tool_calls=writes),
                Reply(tool_calls=[ToolCall("run_tests", {})]),
                Reply(text=f"Fixed {', '.join(c.args['path'] for c in writes)}; tests pass."),
            ]
        )


class NoopModel(_Script):
    def __init__(self, task_dir: Path):
        super().__init__([Reply(tool_calls=[ToolCall("list_files", {})]), Reply(text="The code looks correct to me.")])


class TamperModel(_Script):
    def __init__(self, task_dir: Path):
        tests = sorted(p.name for p in (task_dir / "repo").glob("test_*.py"))
        super().__init__(
            [
                Reply(
                    tool_calls=[
                        ToolCall("write_file", {"path": t, "content": "def test_ok():\n    assert True\n"}) for t in tests
                    ]
                ),
                Reply(tool_calls=[ToolCall("run_tests", {})]),
                Reply(text="All tests pass now."),
            ]
        )


SCRIPTED = {"oracle": OracleModel, "noop": NoopModel, "tamper": TamperModel}
