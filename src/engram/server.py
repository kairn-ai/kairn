"""FastMCP server — Gate 1: 5 graph tools."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from engram.core.graph import GraphEngine
from engram.core.router import ContextRouter
from engram.events.bus import EventBus
from engram.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str)


def create_server(db_path: str) -> FastMCP:
    """Create a FastMCP server with 5 graph tools."""
    mcp = FastMCP("engram", version="0.1.0")

    state: dict[str, Any] = {}
    _lock = asyncio.Lock()

    async def _init() -> tuple[GraphEngine, ContextRouter]:
        async with _lock:
            if "init_failed" in state:
                raise RuntimeError(f"Engram init previously failed for {db_path}")
            if "graph" not in state:
                from pathlib import Path

                try:
                    store = SQLiteStore(Path(db_path))
                    await store.initialize()
                except Exception as e:
                    state["init_failed"] = True
                    logger.error("Failed to initialize database: %s", e)
                    raise RuntimeError(f"Engram init failed: {db_path}") from e
                bus = EventBus()
                state["store"] = store
                state["graph"] = GraphEngine(store, bus)
                state["router"] = ContextRouter(store, bus)
        return state["graph"], state["router"]

    @mcp.tool()
    async def eg_add(
        name: Annotated[str, Field(description="Node name")],
        type: Annotated[
            str,
            Field(
                description="Node type (concept, pattern, etc.)",
            ),
        ],
        namespace: Annotated[
            str,
            Field(
                description="Namespace",
            ),
        ] = "knowledge",
        description: Annotated[
            str | None,
            Field(
                description="Node description",
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(
                description="Tags for categorization",
            ),
        ] = None,
    ) -> str:
        """Add node to knowledge graph. Auto-links via FTS5."""
        if not name or not name.strip():
            return _json({"_v": "1.0", "error": "name is required"})
        if not type or not type.strip():
            return _json({"_v": "1.0", "error": "type is required"})

        graph, router = await _init()
        node = await graph.add_node(
            name=name.strip(),
            type=type.strip(),
            namespace=namespace,
            description=description,
            tags=tags,
        )
        await router.update_routes_for_node(
            node.id,
            node.name,
            node.description,
        )
        result = node.to_response(detail="full")
        result["_v"] = "1.0"
        return _json(result)

    @mcp.tool()
    async def eg_connect(
        source_id: Annotated[str, Field(description="Source node ID")],
        target_id: Annotated[str, Field(description="Target node ID")],
        edge_type: Annotated[str, Field(description="Relationship type")],
        weight: Annotated[
            float,
            Field(
                description="Edge weight 0.0-1.0",
                ge=0.0,
                le=1.0,
            ),
        ] = 1.0,
    ) -> str:
        """Create typed, weighted edge between nodes."""
        if not source_id or not source_id.strip():
            return _json({"_v": "1.0", "error": "source_id is required"})
        if not target_id or not target_id.strip():
            return _json({"_v": "1.0", "error": "target_id is required"})
        if not edge_type or not edge_type.strip():
            return _json({"_v": "1.0", "error": "edge_type is required"})

        graph, _ = await _init()
        try:
            edge = await graph.connect(
                source_id,
                target_id,
                edge_type,
                weight=weight,
            )
            result = edge.to_storage()
            result["_v"] = "1.0"
            return _json(result)
        except ValueError as e:
            return _json({"_v": "1.0", "error": str(e)})

    @mcp.tool()
    async def eg_query(
        text: Annotated[
            str | None,
            Field(
                description="Full-text search query",
            ),
        ] = None,
        namespace: Annotated[
            str | None,
            Field(
                description="Filter by namespace",
            ),
        ] = None,
        node_type: Annotated[
            str | None,
            Field(
                description="Filter by type",
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(
                description="Filter by tags",
            ),
        ] = None,
        detail: Annotated[
            str,
            Field(
                description="summary or full",
            ),
        ] = "summary",
        limit: Annotated[
            int,
            Field(
                description="Max results",
                ge=1,
                le=50,
            ),
        ] = 10,
        offset: Annotated[
            int,
            Field(
                description="Pagination offset",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Search nodes by text, type, tags, or namespace."""
        graph, _ = await _init()
        nodes = await graph.query(
            text=text,
            namespace=namespace,
            node_type=node_type,
            tags=tags,
            limit=limit,
            offset=offset,
        )
        items = [n.to_response(detail=detail) for n in nodes]
        return _json(
            {
                "_v": "1.0",
                "count": len(items),
                "nodes": items,
            }
        )

    @mcp.tool()
    async def eg_remove(
        node_id: Annotated[
            str | None,
            Field(
                description="Node ID to remove",
            ),
        ] = None,
        source_id: Annotated[
            str | None,
            Field(
                description="Edge source ID",
            ),
        ] = None,
        target_id: Annotated[
            str | None,
            Field(
                description="Edge target ID",
            ),
        ] = None,
        edge_type: Annotated[
            str | None,
            Field(
                description="Edge type",
            ),
        ] = None,
    ) -> str:
        """Soft-delete node or edge. Supports undo."""
        graph, _ = await _init()

        if node_id and node_id.strip():
            ok = await graph.remove_node(node_id)
            if ok:
                return _json(
                    {
                        "_v": "1.0",
                        "removed": "node",
                        "id": node_id,
                    }
                )
            return _json(
                {
                    "_v": "1.0",
                    "error": f"Node not found: {node_id}",
                }
            )

        if source_id and target_id and edge_type:
            ok = await graph.disconnect(
                source_id,
                target_id,
                edge_type,
            )
            if ok:
                return _json(
                    {
                        "_v": "1.0",
                        "removed": "edge",
                        "source_id": source_id,
                        "target_id": target_id,
                    }
                )
            return _json({"_v": "1.0", "error": "Edge not found"})

        return _json(
            {
                "_v": "1.0",
                "error": "Provide node_id or (source_id + target_id + edge_type)",
            }
        )

    @mcp.tool()
    async def eg_status() -> str:
        """Graph stats, health, and system overview."""
        graph, _ = await _init()
        stats = await graph.stats()
        stats["_v"] = "1.0"
        return _json(stats)

    return mcp
