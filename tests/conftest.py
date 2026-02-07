"""Shared test fixtures for Kairn."""

from __future__ import annotations

from pathlib import Path

import pytest

from kairn.config import Config
from kairn.storage.sqlite_store import SQLiteStore


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
