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


def test_thought_signature_round_trips():
    part = types.Part(function_call=types.FunctionCall(name="list_files", args={}), thought_signature=b"sig")
    response = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=[part]))])
    from fixer.gemini import _tool_calls

    calls = _tool_calls(response)
    assert [(c.name, c.signature) for c in calls] == [("list_files", b"sig")]
    contents = to_contents(types, [Turn(role="user", text="x"), Turn(role="model", tool_calls=calls)])
    assert contents[1].parts[0].thought_signature == b"sig"


def test_daily_quota_is_not_retried():
    from fixer.gemini import _retry_delay

    class E(Exception):
        code = 429

    assert _retry_delay(E("quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier"), 0) is None
    assert _retry_delay(E("Please retry in 12.5s."), 0) == 13.5
    assert _retry_delay(ValueError("boom"), 0) is None


def test_generate_retries_rate_limit_then_succeeds(monkeypatch):
    import fixer.gemini as g

    class RateLimited(Exception):
        code = 429

    calls = []

    class Models:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RateLimited("Please retry in 0.0s.")
            return "ok"

    model = GeminiModel.__new__(GeminiModel)
    model.client = type("C", (), {"models": Models()})()
    model.model, model.config, model.min_interval, model._last_call = "m", None, 0.0, 0.0
    sleeps = []
    monkeypatch.setattr(g.time, "sleep", sleeps.append)
    assert model._generate([]) == "ok"
    assert len(calls) == 2 and sleeps == [1.0]


def test_generate_gives_up_on_daily_quota(monkeypatch):
    class Daily(Exception):
        code = 429

    class Models:
        def generate_content(self, **kwargs):
            raise Daily("GenerateRequestsPerDayPerProjectPerModel-FreeTier")

    model = GeminiModel.__new__(GeminiModel)
    model.client = type("C", (), {"models": Models()})()
    model.model, model.config, model.min_interval, model._last_call = "m", None, 0.0, 0.0
    with pytest.raises(Daily):
        model._generate([])
