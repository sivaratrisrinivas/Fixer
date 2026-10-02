from fixer.agent import Reply, ToolCall, run_agent
from fixer.tools import Toolbox
from fixer.workspace import Workspace


class Scripted:
    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def step(self, transcript):
        self.seen.append(list(transcript))
        return self.replies.pop(0)


def test_runs_every_tool_call_in_a_turn(tmp_path):
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "b.txt").write_text("B")
    model = Scripted(
        [
            Reply(
                tool_calls=[ToolCall("read_file", {"path": "a.txt"}), ToolCall("read_file", {"path": "b.txt"})],
                usage={"prompt_tokens": 10},
            ),
            Reply(text="read both", usage={"prompt_tokens": 5, "output_tokens": 2}),
        ]
    )
    events = []
    result = run_agent(model, Toolbox(Workspace(tmp_path), lambda p, d: True), "go", on_event=lambda k, p: events.append(k))
    assert result.finished and result.answer == "read both"
    assert result.steps == 2 and result.tool_calls == 2
    tool_turn = model.seen[1][-1]
    assert [r.output for r in tool_turn.results] == ["A", "B"]
    assert result.usage == {"prompt_tokens": 15, "output_tokens": 2}
    assert events == ["model", "tool", "tool", "model"]


def test_stops_at_step_budget(tmp_path):
    class Forever:
        def step(self, transcript):
            return Reply(tool_calls=[ToolCall("list_files", {})])

    result = run_agent(Forever(), Toolbox(Workspace(tmp_path), lambda p, d: True), "loop", max_steps=3)
    assert not result.finished
    assert result.steps == 3 and result.tool_calls == 3
    assert "Stopped after 3 steps" in result.answer
