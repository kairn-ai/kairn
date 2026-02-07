"""Tests for the FastMCP Server (Gate 1: 5 tools)."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

from engram.server import create_server


def _text(result) -> str:
    """Extract text from CallToolResult."""
    return result.content[0].text


def _data(result) -> dict:
    """Extract parsed JSON from CallToolResult."""
    return json.loads(result.content[0].text)


@pytest.fixture
async def client(tmp_path):
    server = create_server(str(tmp_path / "test.db"))
    async with Client(server) as c:
        yield c


async def test_list_tools(client: Client):
    tools = await client.list_tools()
    names = {t.name for t in tools}
    assert "eg_add" in names
    assert "eg_connect" in names
    assert "eg_query" in names
    assert "eg_remove" in names
    assert "eg_status" in names
    assert len(names) == 5


async def test_tool_descriptions_short(client: Client):
    tools = await client.list_tools()
    for tool in tools:
        assert len(tool.description) <= 100, f"{tool.name} description too long"


async def test_eg_add_node(client: Client):
    result = await client.call_tool("eg_add", {
        "name": "JWT Auth",
        "type": "concept",
        "description": "Token-based authentication",
    })
    data = _data(result)
    assert data["name"] == "JWT Auth"
    assert data["_v"] == "1.0"
    assert "id" in data


async def test_eg_add_with_all_fields(client: Client):
    result = await client.call_tool("eg_add", {
        "name": "Redis Cache",
        "type": "pattern",
        "namespace": "idea",
        "description": "In-memory caching layer",
        "tags": ["cache", "redis"],
    })
    data = _data(result)
    assert data["name"] == "Redis Cache"
    assert data["namespace"] == "idea"
    assert "cache" in data["tags"]


async def test_eg_add_minimal(client: Client):
    result = await client.call_tool("eg_add", {
        "name": "Minimal",
        "type": "concept",
    })
    data = _data(result)
    assert data["name"] == "Minimal"


async def test_eg_query_by_text(client: Client):
    await client.call_tool("eg_add", {
        "name": "PostgreSQL",
        "type": "concept",
        "description": "Relational database",
    })
    await client.call_tool("eg_add", {
        "name": "Redis",
        "type": "concept",
        "description": "In-memory cache",
    })

    result = await client.call_tool("eg_query", {"text": "PostgreSQL"})
    data = _data(result)
    assert data["count"] >= 1
    names = [n["name"] for n in data["nodes"]]
    assert "PostgreSQL" in names


async def test_eg_query_by_type(client: Client):
    await client.call_tool("eg_add", {"name": "Pattern A", "type": "pattern"})
    await client.call_tool("eg_add", {"name": "Concept A", "type": "concept"})

    result = await client.call_tool("eg_query", {"node_type": "pattern"})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Pattern A"


async def test_eg_query_by_namespace(client: Client):
    await client.call_tool("eg_add", {"name": "Idea A", "type": "concept", "namespace": "idea"})
    await client.call_tool("eg_add", {"name": "Knowledge A", "type": "concept", "namespace": "knowledge"})

    result = await client.call_tool("eg_query", {"namespace": "idea"})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Idea A"


async def test_eg_query_by_tags(client: Client):
    await client.call_tool("eg_add", {"name": "Tagged", "type": "concept", "tags": ["python"]})
    await client.call_tool("eg_add", {"name": "Untagged", "type": "concept"})

    result = await client.call_tool("eg_query", {"tags": ["python"]})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Tagged"


async def test_eg_query_pagination(client: Client):
    for i in range(15):
        await client.call_tool("eg_add", {"name": f"Node {i}", "type": "concept"})

    result = await client.call_tool("eg_query", {"limit": 5})
    data = _data(result)
    assert data["count"] == 5


async def test_eg_query_detail_full(client: Client):
    await client.call_tool("eg_add", {
        "name": "Full Detail",
        "type": "concept",
        "description": "Detailed node",
        "tags": ["test"],
    })

    result = await client.call_tool("eg_query", {"text": "Full Detail", "detail": "full"})
    data = _data(result)
    assert data["count"] >= 1
    assert "description" in data["nodes"][0]
    assert data["nodes"][0]["description"] == "Detailed node"


async def test_eg_query_empty_result(client: Client):
    result = await client.call_tool("eg_query", {"text": "nonexistent"})
    data = _data(result)
    assert data["count"] == 0
    assert data["nodes"] == []


async def test_eg_connect(client: Client):
    r1 = _data(await client.call_tool("eg_add", {"name": "Auth", "type": "concept"}))
    r2 = _data(await client.call_tool("eg_add", {"name": "JWT", "type": "concept"}))

    result = await client.call_tool("eg_connect", {
        "source_id": r1["id"],
        "target_id": r2["id"],
        "edge_type": "uses",
        "weight": 0.9,
    })
    data = _data(result)
    assert data["type"] == "uses"
    assert data["weight"] == 0.9


async def test_eg_connect_invalid_source(client: Client):
    n = _data(await client.call_tool("eg_add", {"name": "Target", "type": "concept"}))

    result = await client.call_tool("eg_connect", {
        "source_id": "nonexistent",
        "target_id": n["id"],
        "edge_type": "uses",
    })
    data = _data(result)
    assert "error" in data


async def test_eg_remove_node(client: Client):
    n = _data(await client.call_tool("eg_add", {"name": "Removable", "type": "concept"}))

    result = await client.call_tool("eg_remove", {"node_id": n["id"]})
    data = _data(result)
    assert data["removed"] == "node"

    query = _data(await client.call_tool("eg_query", {"text": "Removable"}))
    assert query["count"] == 0


async def test_eg_remove_nonexistent(client: Client):
    result = await client.call_tool("eg_remove", {"node_id": "nope"})
    data = _data(result)
    assert "error" in data


async def test_eg_remove_edge(client: Client):
    n1 = _data(await client.call_tool("eg_add", {"name": "A", "type": "concept"}))
    n2 = _data(await client.call_tool("eg_add", {"name": "B", "type": "concept"}))

    await client.call_tool("eg_connect", {
        "source_id": n1["id"],
        "target_id": n2["id"],
        "edge_type": "related_to",
    })

    result = await client.call_tool("eg_remove", {
        "source_id": n1["id"],
        "target_id": n2["id"],
        "edge_type": "related_to",
    })
    data = _data(result)
    assert data["removed"] == "edge"


async def test_eg_status(client: Client):
    await client.call_tool("eg_add", {"name": "Test", "type": "concept"})

    result = await client.call_tool("eg_status", {})
    data = _data(result)
    assert data["nodes"] >= 1
    assert data["_v"] == "1.0"


async def test_eg_status_empty(client: Client):
    result = await client.call_tool("eg_status", {})
    data = _data(result)
    assert "nodes" in data


async def test_eg_add_returns_valid_json(client: Client):
    result = await client.call_tool("eg_add", {
        "name": "JSON Test",
        "type": "concept",
    })
    data = _data(result)
    assert "id" in data
    assert data["name"] == "JSON Test"
    assert data["_v"] == "1.0"
