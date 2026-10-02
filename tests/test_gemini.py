import pytest

types = pytest.importorskip("google.genai.types")

from fixer.agent import ToolCall, Turn  # noqa: E402
from fixer.gemini import GeminiModel, to_contents, tool_declarations  # noqa: E402
from fixer.tools import Toolbox, ToolResult  # noqa: E402


def test_every_tool_is_declared():
    tool = tool_declarations(types)
    names = [d.name for d in tool.function_declarations]
    assert names == [s["name"] for s in Toolbox.SPECS]
    run_python = tool.function_declarations[names.index("run_python")]
    assert run_python.parameters.properties["args"].type == types.Type.ARRAY
    assert run_python.parameters.required == ["path"]


def test_transcript_maps_to_contents():
    transcript = [
        Turn(role="user", text="fix it"),
        Turn(role="model", tool_calls=[ToolCall("read_file", {"path": "a.py"}), ToolCall("list_files", {})]),
        Turn(role="tool", results=[ToolResult("read_file", {"path": "a.py"}, "x"), ToolResult("list_files", {}, "- a.py")]),
        Turn(role="model", text="done"),
    ]
    contents = to_contents(types, transcript)
    assert [c.role for c in contents] == ["user", "model", "user", "model"]
    assert [p.function_call.name for p in contents[1].parts] == ["read_file", "list_files"]
    assert contents[2].parts[1].function_response.response == {"result": "- a.py"}
    assert contents[3].parts[0].text == "done"


def test_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GeminiModel()
