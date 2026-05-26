from pathlib import Path

import pytest

from llm_wiki.config import WikiConfig
from llm_wiki.scaffold import init_wiki


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A clean temporary project directory."""
    return tmp_path


@pytest.fixture
def wiki_cfg(project: Path) -> WikiConfig:
    """An initialized wiki (generic target) returning its WikiConfig."""
    cfg, _ = init_wiki(project, target="generic")
    return cfg
