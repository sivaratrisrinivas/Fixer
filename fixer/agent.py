"""The agent loop, independent of any model provider.

A model is anything with ``step(transcript) -> Reply``. The loop runs every
tool call the model asks for in a turn (the old version only ran the first one
and silently dropped the rest), feeds the results back, and stops when the
model answers without tool calls or the step budget runs out.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .tools import Toolbox, ToolResult

SYSTEM_PROMPT = """You are Fixer, a careful coding assistant working inside one project directory.

Work in this order:
1. Look around with list_files and read_file before changing anything.
2. Reproduce the problem: run_tests or run_python.
3. Make the smallest change that fixes it with write_file (always the full file content). The user approves every write.
4. Run the tests again. Only say you are done when they pass, and say what you changed.

All paths are relative to the project root. You cannot reach anything outside it."""


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    id: str | None = None
    # Opaque provider data that must be echoed back with the call (Gemini 3 thought signatures).
    signature: bytes | None = None


@dataclass
class Reply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class Turn:
    """One entry in the transcript: a user prompt, a model reply, or tool results."""

    role: str  # "user" | "model" | "tool"
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    results: list[ToolResult] = field(default_factory=list)


class Model(Protocol):
    def step(self, transcript: list[Turn]) -> Reply: ...


@dataclass
class RunResult:
    answer: str
    steps: int
    tool_calls: int
    finished: bool
    writes: list[str]
    transcript: list[Turn]
    usage: dict[str, int]


def run_agent(
    model: Model,
    toolbox: Toolbox,
    prompt: str,
    max_steps: int = 20,
    on_event: Callable[[str, Any], None] | None = None,
) -> RunResult:
    emit = on_event or (lambda kind, payload: None)
    transcript: list[Turn] = [Turn(role="user", text=prompt)]
    usage: dict[str, int] = {}
    calls = 0

    for step in range(1, max_steps + 1):
        reply = model.step(transcript)
        for key, value in reply.usage.items():
            usage[key] = usage.get(key, 0) + value
        transcript.append(Turn(role="model", text=reply.text, tool_calls=list(reply.tool_calls)))
        emit("model", reply)

        if not reply.tool_calls:
            return RunResult(reply.text, step, calls, True, list(toolbox.writes), transcript, usage)

        results = []
        for call in reply.tool_calls:
            result = toolbox.call(call.name, call.args)
            calls += 1
            emit("tool", result)
            results.append(result)
        transcript.append(Turn(role="tool", results=results))

    return RunResult(
        f"Stopped after {max_steps} steps without a final answer.",
        max_steps,
        calls,
        False,
        list(toolbox.writes),
        transcript,
        usage,
    )
