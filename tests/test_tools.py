import pytest

from fixer import tools as tools_mod
from fixer.tools import Toolbox
from fixer.workspace import Workspace


@pytest.fixture
def make_box(tmp_path):
    def _make(approve=lambda path, diff: True):
        (tmp_path / "pkg").mkdir(exist_ok=True)
        (tmp_path / "pkg" / "mod.py").write_text("x = 1\n")
        return Toolbox(Workspace(tmp_path), approve)

    return _make


def test_list_files_hides_noise(make_box, tmp_path):
    box = make_box()
    (tmp_path / "__pycache__").mkdir()
    out = box.call("list_files", {}).output
    assert "pkg/ (dir)" in out
    assert "__pycache__" not in out


def test_read_file_and_errors(make_box, tmp_path):
    box = make_box()
    assert box.call("read_file", {"path": "pkg/mod.py"}).output == "x = 1\n"
    assert box.call("read_file", {"path": "missing.py"}).output.startswith("Error: file not found")
    assert "outside the workspace" in box.call("read_file", {"path": "../etc"}).output
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00")
    assert "not a UTF-8" in box.call("read_file", {"path": "blob.bin"}).output


def test_read_file_truncates(make_box, tmp_path):
    box = make_box()
    (tmp_path / "big.txt").write_text("a" * (tools_mod.MAX_READ_CHARS + 50))
    assert "truncated at" in box.call("read_file", {"path": "big.txt"}).output


def test_write_shows_diff_and_needs_approval(make_box, tmp_path):
    seen = {}

    def approve(path, diff):
        seen["path"], seen["diff"] = path, diff
        return True

    box = make_box(approve)
    out = box.call("write_file", {"path": "pkg/mod.py", "content": "x = 2\n"}).output
    assert seen["path"] == "pkg/mod.py"
    assert "-x = 1" in seen["diff"] and "+x = 2" in seen["diff"]
    assert out.startswith('Wrote "pkg/mod.py"')
    assert (tmp_path / "pkg" / "mod.py").read_text() == "x = 2\n"
    assert box.writes == ["pkg/mod.py"]


def test_rejected_write_leaves_file_alone(make_box, tmp_path):
    box = make_box(lambda path, diff: False)
    out = box.call("write_file", {"path": "pkg/mod.py", "content": "boom\n"}).output
    assert "rejected" in out
    assert (tmp_path / "pkg" / "mod.py").read_text() == "x = 1\n"
    assert box.writes == []


def test_write_new_file_unchanged_and_bad_targets(make_box, tmp_path):
    box = make_box()
    assert box.call("write_file", {"path": "new/dir/a.py", "content": "y\n"}).output.startswith("Wrote")
    assert box.call("write_file", {"path": "new/dir/a.py", "content": "y\n"}).output.startswith("No change")
    assert "is a directory" in box.call("write_file", {"path": "pkg", "content": ""}).output
    assert "outside" in box.call("write_file", {"path": "../evil.py", "content": ""}).output
    assert not (tmp_path.parent / "evil.py").exists()


def test_run_python_passes_args_and_hides_secrets(make_box, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "should-not-leak")
    box = make_box()
    (tmp_path / "show.py").write_text("import os, sys\nprint(sys.argv[1:])\nprint(os.environ.get('GEMINI_API_KEY', 'absent'))\n")
    out = box.call("run_python", {"path": "show.py", "args": ["a", "b"]}).output
    assert "exit code 0" in out
    assert "['a', 'b']" in out
    assert "absent" in out and "should-not-leak" not in out
    assert "not a Python file" in box.call("run_python", {"path": "pkg"}).output
    assert "file not found" in box.call("run_python", {"path": "nope.py"}).output


def test_run_python_timeout(make_box, tmp_path, monkeypatch):
    monkeypatch.setattr(tools_mod, "RUN_TIMEOUT_S", 1)
    box = make_box()
    (tmp_path / "slow.py").write_text("import time\ntime.sleep(5)\n")
    assert "timed out" in box.call("run_python", {"path": "slow.py"}).output


def test_run_tests_reports_failures(make_box, tmp_path):
    box = make_box()
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert 1 == 2\n")
    out = box.call("run_tests", {}).output
    assert "exit code 1" in out and "1 failed" in out
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert 1 == 1\n")
    assert "exit code 0" in box.call("run_tests", {"path": "test_x.py"}).output


def test_unknown_tool_and_bad_args(make_box):
    box = make_box()
    assert box.call("rm_rf", {}).output == 'Error: unknown tool "rm_rf"'
    assert box.call("read_file", {"nope": 1}).output.startswith("Error: bad arguments")


def test_output_is_clipped():
    assert tools_mod._clip("abc", 2).startswith("ab\n[... truncated 1")
