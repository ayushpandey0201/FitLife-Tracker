"""Backwards-compatible entrypoint.

Historically the whole program lived in this file and executed on import. It is
now a thin shim over the packaged CLI (``app.cli``) so the old
``python python_project_vs.py`` invocation keeps working, while the real logic
lives in the testable, layered ``app`` package.
"""

from __future__ import annotations

from app.cli import main

if __name__ == "__main__":
    main()
