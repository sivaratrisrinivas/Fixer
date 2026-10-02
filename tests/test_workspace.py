import os

import pytest

from fixer.workspace import OutsideWorkspace, Workspace


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "src").mkdir()
    return Workspace(root)


def test_inside_paths_resolve(ws):
    assert ws.resolve("src") == ws.root / "src"
    assert ws.resolve(None) == ws.root
    assert ws.resolve("") == ws.root
    assert ws.resolve("src/../src/new.py") == ws.root / "src" / "new.py"


@pytest.mark.parametrize("path", ["..", "../app-secrets/key.txt", "src/../../x", "/etc/passwd"])
def test_escapes_are_rejected(ws, path):
    with pytest.raises(OutsideWorkspace):
        ws.resolve(path)


def test_sibling_with_shared_prefix_is_rejected(ws, tmp_path):
    # The old startswith() check accepted /tmp/x/app-secrets for a root of /tmp/x/app.
    (tmp_path / "app-secrets").mkdir()
    with pytest.raises(OutsideWorkspace):
        ws.resolve("../app-secrets")


def test_symlink_out_of_the_tree_is_rejected(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("nope")
    os.symlink(outside, ws.root / "link")
    with pytest.raises(OutsideWorkspace):
        ws.resolve("link/secret.txt")


def test_relative_display(ws):
    assert ws.relative(ws.root) == "."
    assert ws.relative(ws.root / "src") == "src"
