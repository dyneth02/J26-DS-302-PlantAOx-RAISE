"""Makes ``src/plantaox`` importable without requiring the caller to have
set ``PYTHONPATH=src`` themselves (uvicorn, pytest-without-rootdir, etc.).

Import this module (for its side effect) before importing anything under
``plantaox.*`` from backend code. pytest already gets this via
``pythonpath = ["src", "."]`` in pyproject.toml, but uvicorn does not.
"""

from __future__ import annotations

import sys

from backend.app.core.config import get_settings

_src_path = str(get_settings().src_root)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
