"""Path containment for everything the agent touches.

The old check was ``abspath(path).startswith(abspath(root))``, which lets
``/work/app-secrets`` pass for a root of ``/work/app`` and follows symlinks out of
the tree. Here every path is fully resolved (symlinks included) and must be the
root itself or sit underneath it.
"""

from __future__ import annotations

from pathlib import Path


class OutsideWorkspace(ValueError):
    """Raised when a path would escape the workspace root."""


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise NotADirectoryError(str(self.root))

    def resolve(self, relative: str | None) -> Path:
        rel = (relative or ".").strip() or "."
        candidate = Path(rel)
        if candidate.is_absolute():
            raise OutsideWorkspace(f'"{rel}" is an absolute path; use a path relative to the workspace')
        # resolve() follows symlinks, so a link pointing outside is caught too.
        resolved = (self.root / candidate).resolve(strict=False)
        if resolved != self.root and not resolved.is_relative_to(self.root):
            raise OutsideWorkspace(f'"{rel}" is outside the workspace')
        return resolved

    def relative(self, path: Path) -> str:
        rel = path.relative_to(self.root).as_posix()
        return rel or "."
