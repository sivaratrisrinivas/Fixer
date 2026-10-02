"""Kept for the old ``python main.py "prompt"`` habit. Prefer ``python -m fixer``."""

import sys

from fixer.cli import main

if __name__ == "__main__":
    sys.exit(main())
