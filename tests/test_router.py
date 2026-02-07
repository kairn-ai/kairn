"""Tests for the Context Router."""

from __future__ import annotations

import pytest

from kairn.core.router import ContextRouter
from kairn.events.bus import EventBus
from kairn.storage.sqlite_store import SQLiteStore


@pytest.fixture
async def router(store: SQLiteStore) -> ContextRouter:
    bus = EventBus()
    return ContextRouter(store, bus)


async def test_extract_keywords(router: ContextRouter):
    keywords = router._extract_keywords("How to implement JWT authentication in Python")
    assert "jwt" in keywords
    assert "authentication" in keywords
    assert "python" in keywords
    assert "how" not in keywords
    assert "to" not in keywords


async def test_extract_keywords_dedup(router: ContextRouter):
    keywords = router._extract_keywords("redis redis redis caching caching")
    assert keywords.count("redis") == 1
    assert keywords.count("caching") == 1


async def test_extract_keywords_empty(router: ContextRouter):
    keywords = router._extract_keywords("the is a")
    assert keywords == []


async def test_route_with_matching_routes(router: ContextRouter, store: SQLiteStore):
    await store.insert_node({
        "id": "n1", "namespace": "knowledge", "type": "concept",
        "name": "JWT Auth", "description": "Token auth",
        "properties": None, "tags": None, "created_by": None,
        "visibility": "workspace", "source_type": None, "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": None,
    })
    await store.upsert_route("jwt", ["n1"], 0.9)
    await store.upsert_route("auth", ["n1"], 0.8)

    results = await router.route("How does JWT authentication work?")
    assert len(results) == 1
    assert results[0]["node"]["id"] == "n1"
    assert results[0]["confidence"] == 0.9


async def test_route_no_matches(router: ContextRouter):
    results = await router.route("quantum physics simulation")
    assert results == []


async def test_route_min_confidence_filter(router: ContextRouter, store: SQLiteStore):
    await store.insert_node({
        "id": "n1", "namespace": "knowledge", "type": "concept",
        "name": "Low Conf", "description": None,
        "properties": None, "tags": None, "created_by": None,
        "visibility": "workspace", "source_type": None, "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": None,
    })
    await store.upsert_route("testing", ["n1"], 0.1)

    results = await router.route("testing something", min_confidence=0.3)
    assert len(results) == 0

    results = await router.route("testing something", min_confidence=0.05)
    assert len(results) == 1


async def test_update_routes_for_node(router: ContextRouter, store: SQLiteStore):
    await store.insert_node({
        "id": "n1", "namespace": "knowledge", "type": "concept",
        "name": "Redis Cache", "description": "Distributed caching with Redis",
        "properties": None, "tags": None, "created_by": None,
        "visibility": "workspace", "source_type": None, "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": None,
    })

    await router.update_routes_for_node("n1", "Redis Cache", "Distributed caching with Redis")

    routes = await store.get_routes(["redis"])
    assert len(routes) == 1
    assert "n1" in routes[0]["node_ids"]


async def test_context_summary(router: ContextRouter, store: SQLiteStore):
    await store.insert_node({
        "id": "n1", "namespace": "knowledge", "type": "concept",
        "name": "Auth System", "description": "Authentication architecture",
        "properties": {"lang": "python"}, "tags": ["auth"],
        "created_by": None, "visibility": "workspace",
        "source_type": None, "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": None,
    })
    await store.upsert_route("auth", ["n1"], 0.9)

    result = await router.context("auth system design", detail="summary")
    assert result["_v"] == "1.0"
    assert result["count"] == 1
    assert "description" not in result["nodes"][0]

    result_full = await router.context("auth system design", detail="full")
    assert result_full["count"] == 1
    assert "description" in result_full["nodes"][0]


async def test_context_empty_query(router: ContextRouter):
    result = await router.context("the is a")
    assert result["count"] == 0
    assert result["nodes"] == []
