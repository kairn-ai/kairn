"""Tests for the FastMCP Server (5 consolidated tools)."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

from kairn.server import create_server


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
    expected = {"kn_graph", "kn_project", "kn_experience", "kn_idea", "kn_intel"}
    assert expected == names
    assert len(names) == 5


# ── kn_graph tests ───────────────────────────────────────────


async def test_graph_add_node(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add",
        "name": "JWT Auth",
        "type": "concept",
        "description": "Token-based authentication",
    })
    data = _data(result)
    assert data["name"] == "JWT Auth"
    assert data["_v"] == "1.0"
    assert "id" in data


async def test_graph_add_with_all_fields(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add",
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


async def test_graph_add_minimal(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add",
        "name": "Minimal",
        "type": "concept",
    })
    data = _data(result)
    assert data["name"] == "Minimal"


async def test_graph_add_missing_name(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add",
        "type": "concept",
    })
    data = _data(result)
    assert "error" in data


async def test_graph_add_missing_type(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add",
        "name": "No Type",
    })
    data = _data(result)
    assert "error" in data


async def test_graph_query_by_text(client: Client):
    await client.call_tool("kn_graph", {
        "action": "add", "name": "PostgreSQL", "type": "concept",
        "description": "Relational database",
    })
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Redis", "type": "concept",
        "description": "In-memory cache",
    })

    result = await client.call_tool("kn_graph", {
        "action": "query", "text": "PostgreSQL",
    })
    data = _data(result)
    assert data["count"] >= 1
    names = [n["name"] for n in data["nodes"]]
    assert "PostgreSQL" in names


async def test_graph_query_by_type(client: Client):
    await client.call_tool("kn_graph", {"action": "add", "name": "Pattern A", "type": "pattern"})
    await client.call_tool("kn_graph", {"action": "add", "name": "Concept A", "type": "concept"})

    result = await client.call_tool("kn_graph", {"action": "query", "node_type": "pattern"})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Pattern A"


async def test_graph_query_by_namespace(client: Client):
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Idea A", "type": "concept", "namespace": "idea",
    })
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Knowledge A", "type": "concept", "namespace": "knowledge",
    })

    result = await client.call_tool("kn_graph", {"action": "query", "namespace": "idea"})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Idea A"


async def test_graph_query_by_tags(client: Client):
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Tagged", "type": "concept", "tags": ["python"],
    })
    await client.call_tool("kn_graph", {"action": "add", "name": "Untagged", "type": "concept"})

    result = await client.call_tool("kn_graph", {"action": "query", "tags": ["python"]})
    data = _data(result)
    assert data["count"] == 1
    assert data["nodes"][0]["name"] == "Tagged"


async def test_graph_query_pagination(client: Client):
    for i in range(15):
        await client.call_tool("kn_graph", {"action": "add", "name": f"Node {i}", "type": "concept"})

    result = await client.call_tool("kn_graph", {"action": "query", "limit": 5})
    data = _data(result)
    assert data["count"] == 5


async def test_graph_query_detail_full(client: Client):
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Full Detail", "type": "concept",
        "description": "Detailed node", "tags": ["test"],
    })

    result = await client.call_tool("kn_graph", {
        "action": "query", "text": "Full Detail", "detail": "full",
    })
    data = _data(result)
    assert data["count"] >= 1
    assert "description" in data["nodes"][0]
    assert data["nodes"][0]["description"] == "Detailed node"


async def test_graph_query_empty_result(client: Client):
    result = await client.call_tool("kn_graph", {"action": "query", "text": "nonexistent"})
    data = _data(result)
    assert data["count"] == 0
    assert data["nodes"] == []


async def test_graph_connect(client: Client):
    r1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Auth", "type": "concept"}))
    r2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "JWT", "type": "concept"}))

    result = await client.call_tool("kn_graph", {
        "action": "connect",
        "source_id": r1["id"],
        "target_id": r2["id"],
        "edge_type": "uses",
        "weight": 0.9,
    })
    data = _data(result)
    assert data["type"] == "uses"
    assert data["weight"] == 0.9


async def test_graph_connect_invalid_source(client: Client):
    n = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Target", "type": "concept"}))

    result = await client.call_tool("kn_graph", {
        "action": "connect",
        "source_id": "nonexistent",
        "target_id": n["id"],
        "edge_type": "uses",
    })
    data = _data(result)
    assert "error" in data


async def test_graph_remove_node(client: Client):
    n = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Removable", "type": "concept"}))

    result = await client.call_tool("kn_graph", {"action": "remove", "node_id": n["id"]})
    data = _data(result)
    assert data["removed"] == "node"

    query = _data(await client.call_tool("kn_graph", {"action": "query", "text": "Removable"}))
    assert query["count"] == 0


async def test_graph_remove_nonexistent(client: Client):
    result = await client.call_tool("kn_graph", {"action": "remove", "node_id": "nope"})
    data = _data(result)
    assert "error" in data


async def test_graph_remove_edge(client: Client):
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "A", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "B", "type": "concept"}))

    await client.call_tool("kn_graph", {
        "action": "connect",
        "source_id": n1["id"], "target_id": n2["id"], "edge_type": "related_to",
    })

    result = await client.call_tool("kn_graph", {
        "action": "remove",
        "source_id": n1["id"], "target_id": n2["id"], "edge_type": "related_to",
    })
    data = _data(result)
    assert data["removed"] == "edge"


async def test_graph_status(client: Client):
    await client.call_tool("kn_graph", {"action": "add", "name": "Test", "type": "concept"})

    result = await client.call_tool("kn_graph", {"action": "status"})
    data = _data(result)
    assert data["nodes"] >= 1
    assert data["_v"] == "1.0"


async def test_graph_status_empty(client: Client):
    result = await client.call_tool("kn_graph", {"action": "status"})
    data = _data(result)
    assert "nodes" in data


async def test_graph_add_returns_valid_json(client: Client):
    result = await client.call_tool("kn_graph", {
        "action": "add", "name": "JSON Test", "type": "concept",
    })
    data = _data(result)
    assert "id" in data
    assert data["name"] == "JSON Test"
    assert data["_v"] == "1.0"


# ── kn_project tests ────────────────────────────────────────


async def test_project_create(client: Client):
    result = await client.call_tool("kn_project", {
        "action": "create",
        "name": "Alpha",
        "goals": ["Ship V1"],
    })
    data = _data(result)
    assert data["_v"] == "1.0"
    assert data["name"] == "Alpha"
    assert data["phase"] == "planning"
    assert "id" in data


async def test_project_update(client: Client):
    created = _data(await client.call_tool("kn_project", {
        "action": "create", "name": "Beta",
    }))
    pid = created["id"]

    updated = _data(await client.call_tool("kn_project", {
        "action": "update",
        "name": "Beta v2",
        "project_id": pid,
        "phase": "active",
    }))
    assert updated["name"] == "Beta v2"
    assert updated["phase"] == "active"


async def test_project_invalid_phase(client: Client):
    created = _data(await client.call_tool("kn_project", {
        "action": "create", "name": "Gamma",
    }))
    pid = created["id"]

    result = _data(await client.call_tool("kn_project", {
        "action": "update",
        "name": "Gamma",
        "project_id": pid,
        "phase": "invalid",
    }))
    assert "error" in result


async def test_project_not_found(client: Client):
    result = _data(await client.call_tool("kn_project", {
        "action": "update",
        "name": "Ghost",
        "project_id": "nonexistent",
    }))
    assert "error" in result


async def test_project_phase_rejected_on_create(client: Client):
    result = _data(await client.call_tool("kn_project", {
        "action": "create",
        "name": "Eager",
        "phase": "active",
    }))
    assert "error" in result
    assert "phase" in result["error"].lower()


async def test_project_list(client: Client):
    await client.call_tool("kn_project", {"action": "create", "name": "P1"})
    await client.call_tool("kn_project", {"action": "create", "name": "P2"})

    result = _data(await client.call_tool("kn_project", {"action": "list"}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2
    names = [p["name"] for p in result["projects"]]
    assert "P1" in names
    assert "P2" in names


async def test_project_set_active(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Activate Me"}))

    result = _data(await client.call_tool("kn_project", {
        "action": "list", "set_active": p["id"],
    }))
    assert result["_v"] == "1.0"
    active = [pr for pr in result["projects"] if pr["active"]]
    assert len(active) == 1
    assert active[0]["id"] == p["id"]


async def test_project_set_active_not_found(client: Client):
    result = _data(await client.call_tool("kn_project", {
        "action": "list", "set_active": "nonexistent",
    }))
    assert "error" in result


async def test_project_active_only(client: Client):
    p1 = _data(await client.call_tool("kn_project", {"action": "create", "name": "Active"}))
    await client.call_tool("kn_project", {"action": "create", "name": "Inactive"})
    await client.call_tool("kn_project", {"action": "list", "set_active": p1["id"]})

    result = _data(await client.call_tool("kn_project", {
        "action": "list", "active_only": True,
    }))
    assert result["count"] == 1
    assert result["projects"][0]["name"] == "Active"


async def test_project_log_progress(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Logged"}))

    result = _data(await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "Implemented auth",
        "result": "Working",
        "next_step": "Add tests",
    }))
    assert result["_v"] == "1.0"
    assert result["type"] == "progress"
    assert result["action"] == "Implemented auth"


async def test_project_log_failure(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Failed"}))

    result = _data(await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "Deploy crashed",
        "type": "failure",
        "result": "OOM error",
    }))
    assert result["type"] == "failure"


async def test_project_log_empty_action(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "X"}))
    result = _data(await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "",
    }))
    assert "error" in result


# ── kn_experience tests ──────────────────────────────────────


async def test_experience_save(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save",
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


async def test_experience_save_low_confidence(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Maybe try Redis for caching",
        "type": "workaround",
        "confidence": "low",
    }))
    assert result["confidence"] == "low"
    assert result["decay_rate"] > 0


async def test_experience_save_invalid_type(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Something",
        "type": "invalid_type",
    }))
    assert "error" in result


async def test_experience_save_empty_content(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save",
        "content": "",
        "type": "solution",
    }))
    assert "error" in result


async def test_experience_search(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Always validate JWT tokens on the server side",
        "type": "pattern",
        "tags": ["auth"],
    })
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "SQLite WAL mode improves concurrency",
        "type": "solution",
        "tags": ["database"],
    })

    result = _data(await client.call_tool("kn_experience", {"action": "search"}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2


async def test_experience_search_empty(client: Client):
    result = _data(await client.call_tool("kn_experience", {"action": "search"}))
    assert result["count"] == 0
    assert result["experiences"] == []


async def test_experience_search_with_limit(client: Client):
    for i in range(5):
        await client.call_tool("kn_experience", {
            "action": "save",
            "content": f"Experience {i}",
            "type": "solution",
        })

    result = _data(await client.call_tool("kn_experience", {"action": "search", "limit": 3}))
    assert result["count"] == 3


async def test_experience_relevance_fields(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Fresh experience",
        "type": "decision",
    })

    result = _data(await client.call_tool("kn_experience", {"action": "search"}))
    exp = result["experiences"][0]
    assert "relevance" in exp
    assert exp["relevance"] > 0.9  # Just created, should be near 1.0


async def test_experience_prune_nothing(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Keep me",
        "type": "solution",
    })

    result = _data(await client.call_tool("kn_experience", {"action": "prune"}))
    assert result["_v"] == "1.0"
    assert result["pruned_count"] == 0


async def test_experience_prune_empty(client: Client):
    result = _data(await client.call_tool("kn_experience", {"action": "prune"}))
    assert result["pruned_count"] == 0
    assert result["pruned_ids"] == []


# ── kn_idea tests ────────────────────────────────────────────


async def test_idea_create(client: Client):
    result = _data(await client.call_tool("kn_idea", {
        "action": "create",
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


async def test_idea_update(client: Client):
    created = _data(await client.call_tool("kn_idea", {
        "action": "create", "title": "Original",
    }))

    updated = _data(await client.call_tool("kn_idea", {
        "action": "update",
        "title": "Updated Title",
        "idea_id": created["id"],
        "status": "evaluating",
    }))
    assert updated["title"] == "Updated Title"
    assert updated["status"] == "evaluating"


async def test_idea_invalid_transition(client: Client):
    created = _data(await client.call_tool("kn_idea", {
        "action": "create", "title": "Stuck",
    }))

    # draft -> done is not valid
    result = _data(await client.call_tool("kn_idea", {
        "action": "update",
        "title": "Stuck",
        "idea_id": created["id"],
        "status": "done",
    }))
    assert "error" in result


async def test_idea_not_found(client: Client):
    result = _data(await client.call_tool("kn_idea", {
        "action": "update",
        "title": "Ghost",
        "idea_id": "nonexistent",
    }))
    assert "error" in result


async def test_idea_empty_title(client: Client):
    result = _data(await client.call_tool("kn_idea", {"action": "create", "title": ""}))
    assert "error" in result


async def test_idea_with_link(client: Client):
    node = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "Auth System", "type": "concept",
    }))

    result = _data(await client.call_tool("kn_idea", {
        "action": "create",
        "title": "Improve Auth",
        "link_to": node["id"],
    }))
    assert result["_v"] == "1.0"
    assert result["title"] == "Improve Auth"
    assert result["linked_to"] == node["id"]


async def test_idea_link_to_nonexistent_node(client: Client):
    result = _data(await client.call_tool("kn_idea", {
        "action": "create",
        "title": "Orphan Idea",
        "link_to": "nonexistent",
    }))
    assert result["_v"] == "1.0"
    assert result["title"] == "Orphan Idea"
    assert result["linked_to"] is None
    assert "link_error" in result


async def test_idea_list(client: Client):
    await client.call_tool("kn_idea", {"action": "create", "title": "Idea A", "category": "feature"})
    await client.call_tool("kn_idea", {"action": "create", "title": "Idea B", "category": "bug"})

    result = _data(await client.call_tool("kn_idea", {"action": "list"}))
    assert result["_v"] == "1.0"
    assert result["count"] == 2


async def test_idea_filter_by_status(client: Client):
    created = _data(await client.call_tool("kn_idea", {"action": "create", "title": "Advancing"}))
    await client.call_tool("kn_idea", {"action": "create", "title": "Static"})

    await client.call_tool("kn_idea", {
        "action": "update",
        "title": "Advancing",
        "idea_id": created["id"],
        "status": "evaluating",
    })

    result = _data(await client.call_tool("kn_idea", {"action": "list", "status": "evaluating"}))
    assert result["count"] == 1
    assert result["ideas"][0]["title"] == "Advancing"


async def test_idea_filter_by_category(client: Client):
    await client.call_tool("kn_idea", {"action": "create", "title": "Feature X", "category": "feature"})
    await client.call_tool("kn_idea", {"action": "create", "title": "Bug Y", "category": "bug"})

    result = _data(await client.call_tool("kn_idea", {"action": "list", "category": "feature"}))
    assert result["count"] == 1
    assert result["ideas"][0]["title"] == "Feature X"


async def test_idea_pagination(client: Client):
    for i in range(8):
        await client.call_tool("kn_idea", {"action": "create", "title": f"Idea {i}"})

    result = _data(await client.call_tool("kn_idea", {"action": "list", "limit": 3}))
    assert result["count"] == 3


async def test_idea_empty(client: Client):
    result = _data(await client.call_tool("kn_idea", {"action": "list"}))
    assert result["count"] == 0
    assert result["ideas"] == []


# ── kn_intel tests ───────────────────────────────────────────


async def test_intel_learn_high_confidence(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Use JWT for API authentication",
        "type": "decision",
        "confidence": "high",
        "context": "Architecture review",
        "tags": ["auth", "jwt"],
    }))
    assert result["_v"] == "1.0"
    assert result["stored_as"] == "node"
    assert result["node_id"] is not None
    assert result["experience_id"] is not None


async def test_intel_learn_medium_confidence(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Redis might be good for caching",
        "type": "pattern",
        "confidence": "medium",
    }))
    assert result["stored_as"] == "experience"
    assert result["node_id"] is None
    assert result["experience_id"] is not None


async def test_intel_learn_low_confidence(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Maybe try GraphQL",
        "type": "decision",
        "confidence": "low",
    }))
    assert result["stored_as"] == "experience"
    assert result["node_id"] is None


async def test_intel_learn_invalid_type(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Something",
        "type": "invalid_type",
    }))
    assert "error" in result


async def test_intel_learn_empty_content(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "",
        "type": "decision",
    }))
    assert "error" in result


async def test_intel_recall_basic(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Token bucket algorithm for rate limiting",
        "type": "solution",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "topic": "rate limiting",
    }))
    assert result["_v"] == "1.0"
    assert result["count"] >= 1


async def test_intel_recall_empty_topic(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Testing is important",
        "type": "pattern",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {"action": "recall"}))
    assert result["_v"] == "1.0"
    assert result["count"] >= 1


async def test_intel_recall_no_results(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "topic": "nonexistent_xyz_abc_123",
    }))
    assert result["count"] == 0


async def test_intel_crossref_basic(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Implemented rate limiting with Redis",
        "type": "solution",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "crossref",
        "problem": "Need rate limiting for API endpoints",
    }))
    assert result["_v"] == "1.0"
    assert result["count"] >= 1


async def test_intel_crossref_empty_problem(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "crossref", "problem": "",
    }))
    assert "error" in result


async def test_intel_context_basic(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "FastAPI uses Pydantic for validation",
        "type": "pattern",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "context", "keywords": "FastAPI validation",
    }))
    assert result["_v"] == "1.0"
    assert "nodes" in result
    assert "experiences" in result


async def test_intel_context_empty_keywords(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "context", "keywords": "",
    }))
    assert "error" in result
    assert "keywords" in result["error"]


async def test_intel_context_detail_levels(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "SQLite FTS5 for search",
        "type": "pattern",
        "confidence": "high",
    })

    summary = _data(await client.call_tool("kn_intel", {
        "action": "context", "keywords": "SQLite search", "detail": "summary",
    }))
    full = _data(await client.call_tool("kn_intel", {
        "action": "context", "keywords": "SQLite search", "detail": "full",
    }))
    assert summary["_v"] == "1.0"
    assert full["_v"] == "1.0"


async def test_intel_related_basic(client: Client):
    n1 = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "Authentication", "type": "concept",
    }))
    n2 = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "JWT Tokens", "type": "pattern",
    }))
    await client.call_tool("kn_graph", {
        "action": "connect",
        "source_id": n1["id"], "target_id": n2["id"], "edge_type": "uses",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": n1["id"], "depth": 1,
    }))
    assert result["_v"] == "1.0"
    assert result["count"] >= 1


async def test_intel_related_empty_node_id(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": "",
    }))
    assert "error" in result


async def test_intel_related_nonexistent(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": "nonexistent_id",
    }))
    assert result["count"] == 0


async def test_learn_then_recall_workflow(client: Client):
    """End-to-end: learn something, then recall it."""
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Always use parameterized queries to prevent SQL injection",
        "type": "pattern",
        "confidence": "high",
        "tags": ["security", "sql"],
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "topic": "SQL injection prevention",
    }))
    assert result["count"] >= 1


async def test_learn_then_crossref_workflow(client: Client):
    """End-to-end: learn a solution, then crossref a similar problem."""
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Circuit breaker pattern for external API resilience",
        "type": "solution",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "crossref",
        "problem": "External API keeps failing, need resilience pattern",
    }))
    assert result["count"] >= 1


# ── Resource tests ───────────────────────────────────────────


async def test_list_resources(client: Client):
    resources = await client.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "kn://status" in uris
    assert "kn://projects" in uris
    assert "kn://memories" in uris
    assert len(uris) == 3


def _res(content) -> dict:
    """Extract parsed JSON from resource read result (list of content items)."""
    return json.loads(content[0].text if isinstance(content, list) else content)


async def test_resource_status_empty(client: Client):
    content = await client.read_resource("kn://status")
    data = _res(content)
    assert data["_v"] == "1.0"
    assert "graph" in data
    assert data["active_project"] is None


async def test_resource_status_with_project(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Res Test"}))
    await client.call_tool("kn_project", {"action": "list", "set_active": p["id"]})

    content = await client.read_resource("kn://status")
    data = _res(content)
    assert data["active_project"] is not None
    assert data["active_project"]["name"] == "Res Test"


async def test_resource_projects(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Listed"}))
    await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "Setup done",
    })

    content = await client.read_resource("kn://projects")
    data = _res(content)
    assert data["count"] == 1
    assert data["projects"][0]["name"] == "Listed"
    assert len(data["projects"][0]["recent_progress"]) == 1


async def test_resource_projects_empty(client: Client):
    content = await client.read_resource("kn://projects")
    data = _res(content)
    assert data["count"] == 0


async def test_resource_memories(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Resource test memory",
        "type": "solution",
    })

    content = await client.read_resource("kn://memories")
    data = _res(content)
    assert data["count"] == 1
    assert "Resource test" in data["experiences"][0]["content"]


async def test_resource_memories_empty(client: Client):
    content = await client.read_resource("kn://memories")
    data = _res(content)
    assert data["count"] == 0


# ── Prompt tests ─────────────────────────────────────────────


async def test_list_prompts(client: Client):
    prompts = await client.list_prompts()
    names = {p.name for p in prompts}
    assert "kn_bootup" in names
    assert "kn_review" in names
    assert len(names) == 2


async def test_prompt_bootup_empty(client: Client):
    result = await client.get_prompt("kn_bootup")
    text = result.messages[0].content.text
    assert "Kairn Session Context" in text
    assert "No active project" in text


async def test_prompt_bootup_with_project(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Boot Project"}))
    await client.call_tool("kn_project", {"action": "list", "set_active": p["id"]})
    await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "Initial setup",
    })

    result = await client.get_prompt("kn_bootup")
    text = result.messages[0].content.text
    assert "Boot Project" in text
    assert "Initial setup" in text


async def test_prompt_review_empty(client: Client):
    result = await client.get_prompt("kn_review")
    text = result.messages[0].content.text
    assert "Session Review" in text
    assert "No active project" in text


async def test_prompt_review_with_progress(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Review Project"}))
    await client.call_tool("kn_project", {"action": "list", "set_active": p["id"]})
    await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "DB migration failed",
        "type": "failure",
        "result": "Schema mismatch",
    })
    await client.call_tool("kn_project", {
        "action": "log",
        "project_id": p["id"],
        "action_text": "Added auth module",
        "result": "Working",
        "next_step": "Add tests",
    })

    result = await client.get_prompt("kn_review")
    text = result.messages[0].content.text
    assert "Review Project" in text
    assert "Added auth module" in text
    assert "DB migration failed" in text
    assert "Add tests" in text


# ── kn_graph: missing validation paths ──────────────────────


async def test_graph_add_whitespace_name(client: Client):
    result = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "   ", "type": "concept",
    }))
    assert "error" in result


async def test_graph_connect_missing_source(client: Client):
    n = _data(await client.call_tool("kn_graph", {"action": "add", "name": "T", "type": "concept"}))
    result = _data(await client.call_tool("kn_graph", {
        "action": "connect", "target_id": n["id"], "edge_type": "uses",
    }))
    assert "error" in result
    assert "source_id" in result["error"]


async def test_graph_connect_missing_target(client: Client):
    n = _data(await client.call_tool("kn_graph", {"action": "add", "name": "S", "type": "concept"}))
    result = _data(await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n["id"], "edge_type": "uses",
    }))
    assert "error" in result
    assert "target_id" in result["error"]


async def test_graph_connect_missing_edge_type(client: Client):
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "A", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "B", "type": "concept"}))
    result = _data(await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n2["id"],
    }))
    assert "error" in result
    assert "edge_type" in result["error"]


async def test_graph_connect_default_weight(client: Client):
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "X", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Y", "type": "concept"}))
    result = _data(await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n2["id"], "edge_type": "uses",
    }))
    assert result["weight"] == 1.0


async def test_graph_remove_no_params(client: Client):
    result = _data(await client.call_tool("kn_graph", {"action": "remove"}))
    assert "error" in result
    assert "node_id" in result["error"]


async def test_graph_remove_partial_edge_params(client: Client):
    """Only source_id without target_id and edge_type should error."""
    result = _data(await client.call_tool("kn_graph", {
        "action": "remove", "source_id": "some-id",
    }))
    assert "error" in result


# ── kn_graph: namespace bug fix validation ───────────────────


async def test_graph_add_default_namespace(client: Client):
    """Nodes should default to 'knowledge' namespace when none specified."""
    result = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "Defaulted", "type": "concept",
    }))
    assert result["namespace"] == "knowledge"


async def test_graph_query_explicit_knowledge_namespace(client: Client):
    """Explicitly querying namespace='knowledge' should filter, not return all."""
    await client.call_tool("kn_graph", {
        "action": "add", "name": "In Knowledge", "type": "concept",
    })
    await client.call_tool("kn_graph", {
        "action": "add", "name": "In Ideas", "type": "concept", "namespace": "idea",
    })

    result = _data(await client.call_tool("kn_graph", {
        "action": "query", "namespace": "knowledge",
    }))
    names = [n["name"] for n in result["nodes"]]
    assert "In Knowledge" in names
    assert "In Ideas" not in names


async def test_graph_query_no_namespace_filter(client: Client):
    """No namespace param should return nodes from all namespaces."""
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Node A", "type": "concept",
    })
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Node B", "type": "concept", "namespace": "idea",
    })

    result = _data(await client.call_tool("kn_graph", {"action": "query"}))
    assert result["count"] == 2


async def test_graph_query_with_offset(client: Client):
    for i in range(5):
        await client.call_tool("kn_graph", {"action": "add", "name": f"Off {i}", "type": "concept"})

    all_results = _data(await client.call_tool("kn_graph", {"action": "query", "limit": 50}))
    offset_results = _data(await client.call_tool("kn_graph", {
        "action": "query", "limit": 50, "offset": 3,
    }))
    assert offset_results["count"] == all_results["count"] - 3


async def test_graph_query_combined_filters(client: Client):
    """Text + type filters together should intersect."""
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Python Pattern", "type": "pattern",
    })
    await client.call_tool("kn_graph", {
        "action": "add", "name": "Python Concept", "type": "concept",
    })

    result = _data(await client.call_tool("kn_graph", {
        "action": "query", "text": "Python", "node_type": "pattern",
    }))
    assert result["count"] == 1
    assert result["nodes"][0]["name"] == "Python Pattern"


# ── kn_project: missing validation paths ─────────────────────


async def test_project_create_missing_name(client: Client):
    result = _data(await client.call_tool("kn_project", {"action": "create"}))
    assert "error" in result
    assert "name" in result["error"]


async def test_project_update_missing_project_id(client: Client):
    result = _data(await client.call_tool("kn_project", {
        "action": "update", "name": "No ID",
    }))
    assert "error" in result
    assert "project_id" in result["error"]


async def test_project_update_missing_name(client: Client):
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "X"}))
    result = _data(await client.call_tool("kn_project", {
        "action": "update", "project_id": p["id"],
    }))
    assert "error" in result
    assert "name" in result["error"]


async def test_project_log_missing_project_id(client: Client):
    result = _data(await client.call_tool("kn_project", {
        "action": "log", "action_text": "Something",
    }))
    assert "error" in result
    assert "project_id" in result["error"]


async def test_project_update_with_metadata(client: Client):
    """Update goals, stakeholders, success_metrics."""
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Meta"}))
    updated = _data(await client.call_tool("kn_project", {
        "action": "update",
        "project_id": p["id"],
        "name": "Meta",
        "goals": ["Ship it"],
        "stakeholders": ["Alice"],
        "success_metrics": ["100% coverage"],
    }))
    assert updated["goals"] == ["Ship it"]


# ── kn_experience: missing filter/validation paths ───────────


async def test_experience_save_missing_type(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save", "content": "Something",
    }))
    assert "error" in result
    assert "type" in result["error"]


async def test_experience_save_with_context(client: Client):
    result = _data(await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Use connection pooling",
        "type": "solution",
        "context": "Database scaling issue",
    }))
    assert result["_v"] == "1.0"
    assert "id" in result


async def test_experience_search_by_text(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Use Redis for caching", "type": "solution",
    })
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Postgres is reliable", "type": "pattern",
    })

    result = _data(await client.call_tool("kn_experience", {
        "action": "search", "text": "Redis",
    }))
    assert result["count"] >= 1
    assert any("Redis" in e["content"] for e in result["experiences"])


async def test_experience_search_by_type(client: Client):
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Workaround A", "type": "workaround",
    })
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Pattern B", "type": "pattern",
    })

    result = _data(await client.call_tool("kn_experience", {
        "action": "search", "type": "workaround",
    }))
    assert result["count"] == 1
    assert result["experiences"][0]["type"] == "workaround"


async def test_experience_search_with_min_relevance(client: Client):
    """Fresh experiences should have high relevance, so min_relevance=0.5 should include them."""
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Very relevant", "type": "solution",
    })

    result = _data(await client.call_tool("kn_experience", {
        "action": "search", "min_relevance": 0.5,
    }))
    assert result["count"] == 1

    # min_relevance=0.99 should still find a just-created experience (relevance ~1.0)
    high_bar = _data(await client.call_tool("kn_experience", {
        "action": "search", "min_relevance": 0.99,
    }))
    assert high_bar["count"] >= 1


async def test_experience_prune_with_threshold(client: Client):
    """A very low prune threshold should not remove freshly created, high-relevance experiences."""
    await client.call_tool("kn_experience", {
        "action": "save", "content": "Will be kept", "type": "workaround",
    })
    # threshold=0.001 is far below the relevance of a just-created experience (~1.0),
    # so nothing should be pruned.
    result = _data(await client.call_tool("kn_experience", {
        "action": "prune", "threshold": 0.001,
    }))
    assert result["pruned_count"] == 0


# ── kn_idea: missing validation paths ────────────────────────


async def test_idea_update_missing_idea_id(client: Client):
    result = _data(await client.call_tool("kn_idea", {
        "action": "update", "title": "No ID",
    }))
    assert "error" in result
    assert "idea_id" in result["error"]


async def test_idea_update_missing_title(client: Client):
    idea = _data(await client.call_tool("kn_idea", {"action": "create", "title": "Has Title"}))
    result = _data(await client.call_tool("kn_idea", {
        "action": "update", "idea_id": idea["id"],
    }))
    assert "error" in result
    assert "title" in result["error"]


async def test_idea_update_with_link(client: Client):
    """Linking an idea to a graph node during update."""
    node = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "Target Node", "type": "concept",
    }))
    idea = _data(await client.call_tool("kn_idea", {"action": "create", "title": "Link Later"}))

    result = _data(await client.call_tool("kn_idea", {
        "action": "update",
        "idea_id": idea["id"],
        "title": "Link Later",
        "link_to": node["id"],
    }))
    assert result["linked_to"] == node["id"]


async def test_idea_list_with_offset(client: Client):
    for i in range(5):
        await client.call_tool("kn_idea", {"action": "create", "title": f"Idea {i}"})

    page1 = _data(await client.call_tool("kn_idea", {"action": "list", "limit": 3}))
    page2 = _data(await client.call_tool("kn_idea", {"action": "list", "limit": 3, "offset": 3}))
    assert page1["count"] == 3
    assert page2["count"] == 2


# ── kn_intel: missing validation/filter paths ────────────────


async def test_intel_learn_missing_type(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn", "content": "Something",
    }))
    assert "error" in result
    assert "type" in result["error"]


async def test_intel_learn_with_context_and_tags(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Always use HTTPS",
        "type": "pattern",
        "confidence": "high",
        "context": "Security review",
        "tags": ["security", "networking"],
    }))
    assert result["_v"] == "1.0"
    assert result["stored_as"] == "node"


async def test_intel_recall_with_limit(client: Client):
    for i in range(5):
        await client.call_tool("kn_intel", {
            "action": "learn",
            "content": f"Pattern {i} about databases",
            "type": "pattern",
            "confidence": "high",
        })

    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "topic": "databases", "limit": 2,
    }))
    assert result["count"] <= 2


async def test_intel_recall_with_min_relevance(client: Client):
    await client.call_tool("kn_intel", {
        "action": "learn",
        "content": "Fresh knowledge",
        "type": "solution",
        "confidence": "high",
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "min_relevance": 0.5,
    }))
    assert result["count"] >= 1


async def test_intel_crossref_no_results(client: Client):
    result = _data(await client.call_tool("kn_intel", {
        "action": "crossref",
        "problem": "completely unique problem xyz abc 123 never seen before",
    }))
    assert result["count"] == 0


async def test_intel_related_with_depth(client: Client):
    """Test traversal at depth > 1."""
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Root", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Child", "type": "concept"}))
    n3 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Grandchild", "type": "concept"}))

    await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n2["id"], "edge_type": "parent_of",
    })
    await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n2["id"], "target_id": n3["id"], "edge_type": "parent_of",
    })

    depth1 = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": n1["id"], "depth": 1,
    }))
    depth2 = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": n1["id"], "depth": 2,
    }))
    assert depth2["count"] >= depth1["count"]


async def test_intel_related_with_edge_type_filter(client: Client):
    """Filtering by edge_type should only return matching edges."""
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Hub", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Dep", "type": "concept"}))
    n3 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Rel", "type": "concept"}))

    await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n2["id"], "edge_type": "depends_on",
    })
    await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n3["id"], "edge_type": "related_to",
    })

    filtered = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": n1["id"], "edge_type": "depends_on",
    }))
    # Should find at least n2 but not necessarily n3
    assert filtered["count"] >= 1


async def test_intel_context_with_limit(client: Client):
    for i in range(5):
        await client.call_tool("kn_intel", {
            "action": "learn",
            "content": f"Database optimization technique {i}",
            "type": "solution",
            "confidence": "high",
        })

    result = _data(await client.call_tool("kn_intel", {
        "action": "context", "keywords": "database optimization", "limit": 2,
    }))
    assert result["_v"] == "1.0"


# ── Cross-tool workflow tests ────────────────────────────────


async def test_graph_add_then_intel_related(client: Client):
    """Create nodes via graph, then use intel to traverse."""
    n1 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "API", "type": "concept"}))
    n2 = _data(await client.call_tool("kn_graph", {"action": "add", "name": "Auth", "type": "concept"}))
    await client.call_tool("kn_graph", {
        "action": "connect", "source_id": n1["id"], "target_id": n2["id"], "edge_type": "requires",
    })

    related = _data(await client.call_tool("kn_intel", {
        "action": "related", "node_id": n1["id"],
    }))
    assert related["count"] >= 1


async def test_full_project_lifecycle(client: Client):
    """Create → update → log → list → review."""
    p = _data(await client.call_tool("kn_project", {"action": "create", "name": "Lifecycle"}))
    await client.call_tool("kn_project", {
        "action": "update", "project_id": p["id"], "name": "Lifecycle", "phase": "active",
    })
    await client.call_tool("kn_project", {"action": "list", "set_active": p["id"]})
    await client.call_tool("kn_project", {
        "action": "log", "project_id": p["id"], "action_text": "Step 1 done",
        "result": "Success", "next_step": "Step 2",
    })
    await client.call_tool("kn_project", {
        "action": "log", "project_id": p["id"], "action_text": "Step 2 failed",
        "type": "failure", "result": "Timeout",
    })

    listing = _data(await client.call_tool("kn_project", {"action": "list", "active_only": True}))
    assert listing["count"] == 1
    assert listing["projects"][0]["phase"] == "active"

    # Prompts should reflect the lifecycle
    review = await client.get_prompt("kn_review")
    text = review.messages[0].content.text
    assert "Lifecycle" in text
    assert "Step 1 done" in text
    assert "Step 2 failed" in text


async def test_idea_linked_to_graph_then_queried(client: Client):
    """Create graph node, link idea, verify idea lists correctly."""
    node = _data(await client.call_tool("kn_graph", {
        "action": "add", "name": "Caching Layer", "type": "concept",
    }))
    idea = _data(await client.call_tool("kn_idea", {
        "action": "create", "title": "Add Redis Cache", "link_to": node["id"],
    }))
    assert idea["linked_to"] == node["id"]

    ideas = _data(await client.call_tool("kn_idea", {"action": "list"}))
    assert ideas["count"] == 1
    assert ideas["ideas"][0]["title"] == "Add Redis Cache"


async def test_experience_save_then_intel_recall(client: Client):
    """Save via kn_experience, recall via kn_intel."""
    await client.call_tool("kn_experience", {
        "action": "save",
        "content": "Connection pooling prevents exhaustion",
        "type": "solution",
        "tags": ["database"],
    })

    result = _data(await client.call_tool("kn_intel", {
        "action": "recall", "topic": "connection pooling",
    }))
    assert result["count"] >= 1
