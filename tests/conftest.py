from __future__ import annotations

import types
from pathlib import Path

import pytest

BUILDER = Path(__file__).resolve().parent.parent / "scripts" / "build_assets.py"


@pytest.fixture
def builder() -> types.ModuleType:
    """scripts/build_assets.py compiled from source, so a stale __pycache__ can't mask an edit."""
    module = types.ModuleType("build_assets")
    module.__file__ = str(BUILDER)
    source = compile(BUILDER.read_text(encoding="utf-8"), BUILDER, "exec")
    exec(source, module.__dict__)  # noqa: S102 -- our own generator, compiled to bypass .pyc
    return module
