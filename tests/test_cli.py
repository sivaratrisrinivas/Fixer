import io

from fixer.cli import make_approver


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def test_yes_flag_approves():
    out = io.StringIO()
    assert make_approver(True, io.StringIO(), out)("a.py", "+x") is True
    assert "+x" in out.getvalue()


def test_no_terminal_refuses_by_default():
    out = io.StringIO()
    assert make_approver(False, io.StringIO(), out)("a.py", "+x") is False
    assert "--yes" in out.getvalue()


def test_terminal_answer_decides():
    assert make_approver(False, FakeTTY("y\n"), io.StringIO())("a.py", "") is True
    assert make_approver(False, FakeTTY("\n"), io.StringIO())("a.py", "") is False


def test_missing_key_exits_cleanly(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    from fixer.cli import main

    assert main(["hello"]) == 2
    assert "GEMINI_API_KEY" in capsys.readouterr().err
