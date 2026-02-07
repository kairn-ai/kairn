"""Shared test fixtures for Engram."""

from __future__ import annotations

from pathlib import Path

import pytest

from engram.config import Config
from engram.storage.sqlite_store import SQLiteStore


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
async def store(tmp_db: Path) -> SQLiteStore:
    s = SQLiteStore(tmp_db)
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(workspace_path=tmp_path)
