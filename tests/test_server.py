"""Tests for the FastMCP Server (Gate 2: 13 tools)."""

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
    expected = {
        "eg_add", "eg_connect", "eg_query", "eg_remove", "eg_status",
        "eg_project", "eg_projects", "eg_log",
        "eg_save", "eg_memories", "eg_prune",
        "eg_idea", "eg_ideas",
    }
    assert expected.issubset(names)
    assert len(names) == 13


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


# ── Project Memory tool tests ────────────────────────────────


async def test_eg_project_create(client: Client):
    result = await client.call_tool("eg_project", {
        "name": "Alpha",
        "goals": ["Ship V1"],
    })
    data = _data(result)
    assert data["_v"] == "1.0"
    assert data["name"] == "Alpha"
    assert data["phase"] == "planning"
    assert "id" in data


async def test_eg_project_update(client: Client):
    created = _data(await client.call_tool("eg_project", {"name": "Beta"}))
    pid = created["id"]

    updated = _data(await client.call_tool("eg_project", {
        "name": "Beta v2",
        "project_id": pid,
        "phase": "active",
    }))
    assert updated["name"] == "Beta v2"
    assert updated["phase"] == "active"


async def test_eg_project_invalid_phase(client: Client):
    created = _data(await client.call_tool("eg_project", {"name": "Gamma"}))
    pid = created["id"]

    result = _data(await client.call_tool("eg_project", {
        "name": "Gamma",
        "project_id": pid,
        "phase": "invalid",
    }))
    assert "error" in result


async def test_eg_project_not_found(client: Client):
    result = _data(await client.call_tool("eg_project", {
        "name": "Ghost",
        "project_id": "nonexistent",
    }))
    assert "error" in result


async def test_eg_project_phase_rejected_on_create(client: Client):
    result = _data(await client.call_tool("eg_project", {
        "name": "Eager",
        "phase": "active",
    }))
    assert "error" in result
    assert "phase" in result["error"].lower()


async def test_eg_projects_list(client: Client):
    await client.call_tool("eg_project", {"name": "P1"})
    await client.call_tool("eg_project", {"name": "P2"})

    result = _data(await client.call_tool("eg_projects", {}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2
    names = [p["name"] for p in result["projects"]]
    assert "P1" in names
    assert "P2" in names


async def test_eg_projects_set_active(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Activate Me"}))

    result = _data(await client.call_tool("eg_projects", {
        "set_active": p["id"],
    }))
    assert result["_v"] == "1.0"
    active = [pr for pr in result["projects"] if pr["active"]]
    assert len(active) == 1
    assert active[0]["id"] == p["id"]


async def test_eg_projects_set_active_not_found(client: Client):
    result = _data(await client.call_tool("eg_projects", {
        "set_active": "nonexistent",
    }))
    assert "error" in result


async def test_eg_projects_active_only(client: Client):
    p1 = _data(await client.call_tool("eg_project", {"name": "Active"}))
    await client.call_tool("eg_project", {"name": "Inactive"})
    await client.call_tool("eg_projects", {"set_active": p1["id"]})

    result = _data(await client.call_tool("eg_projects", {"active_only": True}))
    assert result["count"] == 1
    assert result["projects"][0]["name"] == "Active"


async def test_eg_log_progress(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Logged"}))

    result = _data(await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "Implemented auth",
        "result": "Working",
        "next_step": "Add tests",
    }))
    assert result["_v"] == "1.0"
    assert result["type"] == "progress"
    assert result["action"] == "Implemented auth"


async def test_eg_log_failure(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Failed"}))

    result = _data(await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "Deploy crashed",
        "type": "failure",
        "result": "OOM error",
    }))
    assert result["type"] == "failure"


async def test_eg_log_empty_action(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "X"}))
    result = _data(await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "",
    }))
    assert "error" in result


# ── Experience Memory tool tests ─────────────────────────────


async def test_eg_save(client: Client):
    result = _data(await client.call_tool("eg_save", {
        "content": "Use WAL mode for concurrent SQLite access",
        "type": "solution",
        "confidence": "high",
        "tags": ["sqlite", "performance"],
    }))
    assert result["_v"] == "1.0"
    assert result["type"] == "solution"
    assert result["confidence"] == "high"
    assert result["score"] == 1.0
    assert "id" in result
    assert result["decay_rate"] > 0


async def test_eg_save_low_confidence(client: Client):
    result = _data(await client.call_tool("eg_save", {
        "content": "Maybe try Redis for caching",
        "type": "workaround",
        "confidence": "low",
    }))
    assert result["confidence"] == "low"
    # Low confidence should decay 4x faster
    assert result["decay_rate"] > 0


async def test_eg_save_invalid_type(client: Client):
    result = _data(await client.call_tool("eg_save", {
        "content": "Something",
        "type": "invalid_type",
    }))
    assert "error" in result


async def test_eg_save_empty_content(client: Client):
    result = _data(await client.call_tool("eg_save", {
        "content": "",
        "type": "solution",
    }))
    assert "error" in result


async def test_eg_memories_search(client: Client):
    await client.call_tool("eg_save", {
        "content": "Always validate JWT tokens on the server side",
        "type": "pattern",
        "tags": ["auth"],
    })
    await client.call_tool("eg_save", {
        "content": "SQLite WAL mode improves concurrency",
        "type": "solution",
        "tags": ["database"],
    })

    result = _data(await client.call_tool("eg_memories", {}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2


async def test_eg_memories_empty(client: Client):
    result = _data(await client.call_tool("eg_memories", {}))
    assert result["count"] == 0
    assert result["experiences"] == []


async def test_eg_memories_with_limit(client: Client):
    for i in range(5):
        await client.call_tool("eg_save", {
            "content": f"Experience {i}",
            "type": "solution",
        })

    result = _data(await client.call_tool("eg_memories", {"limit": 3}))
    assert result["count"] == 3


async def test_eg_memories_relevance_fields(client: Client):
    await client.call_tool("eg_save", {
        "content": "Fresh experience",
        "type": "decision",
    })

    result = _data(await client.call_tool("eg_memories", {}))
    exp = result["experiences"][0]
    assert "relevance" in exp
    assert exp["relevance"] > 0.9  # Just created, should be near 1.0


async def test_eg_prune_nothing(client: Client):
    # Fresh experience should not be pruned
    await client.call_tool("eg_save", {
        "content": "Keep me",
        "type": "solution",
    })

    result = _data(await client.call_tool("eg_prune", {}))
    assert result["_v"] == "1.0"
    assert result["pruned_count"] == 0


async def test_eg_prune_empty(client: Client):
    result = _data(await client.call_tool("eg_prune", {}))
    assert result["pruned_count"] == 0
    assert result["pruned_ids"] == []


# ── Idea tool tests ──────────────────────────────────────────


async def test_eg_idea_create(client: Client):
    result = _data(await client.call_tool("eg_idea", {
        "title": "Build a CLI",
        "category": "feature",
        "score": 8.5,
    }))
    assert result["_v"] == "1.0"
    assert result["title"] == "Build a CLI"
    assert result["status"] == "draft"
    assert result["category"] == "feature"
    assert result["score"] == 8.5
    assert "id" in result


async def test_eg_idea_update(client: Client):
    created = _data(await client.call_tool("eg_idea", {"title": "Original"}))

    updated = _data(await client.call_tool("eg_idea", {
        "title": "Updated Title",
        "idea_id": created["id"],
        "status": "evaluating",
    }))
    assert updated["title"] == "Updated Title"
    assert updated["status"] == "evaluating"


async def test_eg_idea_invalid_transition(client: Client):
    created = _data(await client.call_tool("eg_idea", {"title": "Stuck"}))

    # draft -> done is not valid (must go through evaluating, approved, implementing)
    result = _data(await client.call_tool("eg_idea", {
        "title": "Stuck",
        "idea_id": created["id"],
        "status": "done",
    }))
    assert "error" in result


async def test_eg_idea_not_found(client: Client):
    result = _data(await client.call_tool("eg_idea", {
        "title": "Ghost",
        "idea_id": "nonexistent",
    }))
    assert "error" in result


async def test_eg_idea_empty_title(client: Client):
    result = _data(await client.call_tool("eg_idea", {"title": ""}))
    assert "error" in result


async def test_eg_idea_with_link(client: Client):
    # Create a node to link to
    node = _data(await client.call_tool("eg_add", {
        "name": "Auth System",
        "type": "concept",
    }))

    result = _data(await client.call_tool("eg_idea", {
        "title": "Improve Auth",
        "link_to": node["id"],
    }))
    assert result["_v"] == "1.0"
    assert result["title"] == "Improve Auth"
    assert result["linked_to"] == node["id"]


async def test_eg_idea_link_to_nonexistent_node(client: Client):
    result = _data(await client.call_tool("eg_idea", {
        "title": "Orphan Idea",
        "link_to": "nonexistent",
    }))
    assert result["_v"] == "1.0"
    assert result["title"] == "Orphan Idea"
    assert result["linked_to"] is None
    assert "link_error" in result


async def test_eg_ideas_list(client: Client):
    await client.call_tool("eg_idea", {"title": "Idea A", "category": "feature"})
    await client.call_tool("eg_idea", {"title": "Idea B", "category": "bug"})

    result = _data(await client.call_tool("eg_ideas", {}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2


async def test_eg_ideas_filter_by_status(client: Client):
    created = _data(await client.call_tool("eg_idea", {"title": "Advancing"}))
    await client.call_tool("eg_idea", {"title": "Static"})

    # Advance first idea to evaluating
    await client.call_tool("eg_idea", {
        "title": "Advancing",
        "idea_id": created["id"],
        "status": "evaluating",
    })

    result = _data(await client.call_tool("eg_ideas", {"status": "evaluating"}))
    assert result["count"] == 1
    assert result["ideas"][0]["title"] == "Advancing"


async def test_eg_ideas_filter_by_category(client: Client):
    await client.call_tool("eg_idea", {"title": "Feature X", "category": "feature"})
    await client.call_tool("eg_idea", {"title": "Bug Y", "category": "bug"})

    result = _data(await client.call_tool("eg_ideas", {"category": "feature"}))
    assert result["count"] == 1
    assert result["ideas"][0]["title"] == "Feature X"


async def test_eg_ideas_pagination(client: Client):
    for i in range(8):
        await client.call_tool("eg_idea", {"title": f"Idea {i}"})

    result = _data(await client.call_tool("eg_ideas", {"limit": 3}))
    assert result["count"] == 3


async def test_eg_ideas_empty(client: Client):
    result = _data(await client.call_tool("eg_ideas", {}))
    assert result["count"] == 0
    assert result["ideas"] == []


# ── Resource tests ───────────────────────────────────────────


async def test_list_resources(client: Client):
    resources = await client.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "eg://status" in uris
    assert "eg://projects" in uris
    assert "eg://memories" in uris
    assert len(uris) == 3


def _res(content) -> dict:
    """Extract parsed JSON from resource read result (list of content items)."""
    return json.loads(content[0].text if isinstance(content, list) else content)


async def test_resource_status_empty(client: Client):
    content = await client.read_resource("eg://status")
    data = _res(content)
    assert data["_v"] == "1.0"
    assert "graph" in data
    assert data["active_project"] is None


async def test_resource_status_with_project(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Res Test"}))
    await client.call_tool("eg_projects", {"set_active": p["id"]})

    content = await client.read_resource("eg://status")
    data = _res(content)
    assert data["active_project"] is not None
    assert data["active_project"]["name"] == "Res Test"


async def test_resource_projects(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Listed"}))
    await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "Setup done",
    })

    content = await client.read_resource("eg://projects")
    data = _res(content)
    assert data["count"] == 1
    assert data["projects"][0]["name"] == "Listed"
    assert len(data["projects"][0]["recent_progress"]) == 1


async def test_resource_projects_empty(client: Client):
    content = await client.read_resource("eg://projects")
    data = _res(content)
    assert data["count"] == 0


async def test_resource_memories(client: Client):
    await client.call_tool("eg_save", {
        "content": "Resource test memory",
        "type": "solution",
    })

    content = await client.read_resource("eg://memories")
    data = _res(content)
    assert data["count"] == 1
    assert "Resource test" in data["experiences"][0]["content"]


async def test_resource_memories_empty(client: Client):
    content = await client.read_resource("eg://memories")
    data = _res(content)
    assert data["count"] == 0


# ── Prompt tests ─────────────────────────────────────────────


async def test_list_prompts(client: Client):
    prompts = await client.list_prompts()
    names = {p.name for p in prompts}
    assert "eg_bootup" in names
    assert "eg_review" in names
    assert len(names) == 2


async def test_prompt_bootup_empty(client: Client):
    result = await client.get_prompt("eg_bootup")
    text = result.messages[0].content.text
    assert "Engram Session Context" in text
    assert "No active project" in text


async def test_prompt_bootup_with_project(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Boot Project"}))
    await client.call_tool("eg_projects", {"set_active": p["id"]})
    await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "Initial setup",
    })

    result = await client.get_prompt("eg_bootup")
    text = result.messages[0].content.text
    assert "Boot Project" in text
    assert "Initial setup" in text


async def test_prompt_review_empty(client: Client):
    result = await client.get_prompt("eg_review")
    text = result.messages[0].content.text
    assert "Session Review" in text
    assert "No active project" in text


async def test_prompt_review_with_progress(client: Client):
    p = _data(await client.call_tool("eg_project", {"name": "Review Project"}))
    await client.call_tool("eg_projects", {"set_active": p["id"]})
    await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "DB migration failed",
        "type": "failure",
        "result": "Schema mismatch",
    })
    # Log progress last so most recent entry has next_step
    await client.call_tool("eg_log", {
        "project_id": p["id"],
        "action": "Added auth module",
        "result": "Working",
        "next_step": "Add tests",
    })

    result = await client.get_prompt("eg_review")
    text = result.messages[0].content.text
    assert "Review Project" in text
    assert "Added auth module" in text
    assert "DB migration failed" in text
    assert "Add tests" in text
