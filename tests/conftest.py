from pathlib import Path

import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A clean temporary project directory."""
    return tmp_path
