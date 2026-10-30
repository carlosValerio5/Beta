from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from beta_data.layout import Lakehouse
from beta_data.seed import seed


@pytest.fixture
def lake(tmp_path: Path) -> Lakehouse:
    return Lakehouse(tmp_path / "data")


@pytest.fixture(scope="session")
def seeded_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("seeded") / "data"
    seed(Lakehouse(root), count=3)
    return root


@pytest.fixture
def seeded(seeded_root: Path, tmp_path: Path) -> Lakehouse:
    """A fresh copy of the seeded lake per test, so jobs can write freely."""
    copy = tmp_path / "data"
    shutil.copytree(seeded_root, copy)
    return Lakehouse(copy)
