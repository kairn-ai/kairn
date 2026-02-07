"""FastMCP server — Gate 2: 13 tools, 3 resources, 2 prompts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from engram.core.experience import ExperienceEngine
from engram.core.graph import GraphEngine
from engram.core.ideas import IdeaEngine
from engram.core.memory import ProjectMemory
from engram.core.router import ContextRouter
from engram.events.bus import EventBus
from engram.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str)


def create_server(db_path: str) -> FastMCP:
    """Create a FastMCP server with 13 tools (5 graph + 3 project + 3 experience + 2 ideas)."""
    mcp = FastMCP("engram", version="0.1.0")

    state: dict[str, Any] = {}
    _lock = asyncio.Lock()

    async def _init() -> dict[str, Any]:
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
                state["bus"] = bus
                state["graph"] = GraphEngine(store, bus)
                state["router"] = ContextRouter(store, bus)
                state["memory"] = ProjectMemory(store, bus)
                state["experience"] = ExperienceEngine(store, bus)
                state["ideas"] = IdeaEngine(store, bus)
        return state

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

        s = await _init()
        node = await s["graph"].add_node(
            name=name.strip(),
            type=type.strip(),
            namespace=namespace,
            description=description,
            tags=tags,
        )
        await s["router"].update_routes_for_node(
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

        s = await _init()
        try:
            edge = await s["graph"].connect(
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
        s = await _init()
        nodes = await s["graph"].query(
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
        s = await _init()

        if node_id and node_id.strip():
            ok = await s["graph"].remove_node(node_id)
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
            ok = await s["graph"].disconnect(
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
        s = await _init()
        stats = await s["graph"].stats()
        stats["_v"] = "1.0"
        return _json(stats)

    # ── Project Memory tools (3) ───────────────────────────────

    @mcp.tool()
    async def eg_project(
        name: Annotated[str, Field(description="Project name")],
        project_id: Annotated[
            str | None,
            Field(description="Project ID (omit to create new)"),
        ] = None,
        phase: Annotated[
            str | None,
            Field(description="Phase: planning|active|paused|done"),
        ] = None,
        goals: Annotated[
            list[str] | None,
            Field(description="Project goals"),
        ] = None,
        stakeholders: Annotated[
            list[str] | None,
            Field(description="Stakeholders"),
        ] = None,
        success_metrics: Annotated[
            list[str] | None,
            Field(description="Success metrics / KPIs"),
        ] = None,
    ) -> str:
        """Create or update project (upsert)."""
        if not name or not name.strip():
            return _json({"_v": "1.0", "error": "name is required"})

        s = await _init()
        mem = s["memory"]

        if project_id:
            # Update existing
            updates: dict[str, Any] = {"name": name.strip()}
            if phase is not None:
                updates["phase"] = phase
            if goals is not None:
                updates["goals"] = goals
            if stakeholders is not None:
                updates["stakeholders"] = stakeholders
            if success_metrics is not None:
                updates["success_metrics"] = success_metrics
            try:
                project = await mem.update_project(project_id, **updates)
            except ValueError as e:
                return _json({"_v": "1.0", "error": str(e)})
            if not project:
                return _json({"_v": "1.0", "error": f"Project not found: {project_id}"})
        else:
            # Create new — phase always starts at "planning"
            if phase is not None:
                return _json({
                    "_v": "1.0",
                    "error": "phase cannot be set on create (starts at planning)",
                })
            try:
                project = await mem.create_project(
                    name=name.strip(),
                    goals=goals,
                    stakeholders=stakeholders,
                    success_metrics=success_metrics,
                )
            except ValueError as e:
                return _json({"_v": "1.0", "error": str(e)})

        result = {
            "_v": "1.0",
            "id": project.id,
            "name": project.name,
            "phase": project.phase,
            "active": project.active,
            "goals": project.goals,
        }
        return _json(result)

    @mcp.tool()
    async def eg_projects(
        active_only: Annotated[
            bool,
            Field(description="Only show active projects"),
        ] = False,
        set_active: Annotated[
            str | None,
            Field(description="Project ID to set as active"),
        ] = None,
    ) -> str:
        """List projects and switch active."""
        s = await _init()
        mem = s["memory"]

        if set_active:
            ok = await mem.set_active_project(set_active)
            if not ok:
                return _json({"_v": "1.0", "error": f"Project not found: {set_active}"})

        projects = await mem.list_projects(active_only=active_only)
        items = [
            {
                "id": p.id,
                "name": p.name,
                "phase": p.phase,
                "active": p.active,
            }
            for p in projects
        ]
        return _json({"_v": "1.0", "count": len(items), "projects": items})

    @mcp.tool()
    async def eg_log(
        project_id: Annotated[str, Field(description="Project ID")],
        action: Annotated[str, Field(description="What was done or what failed")],
        type: Annotated[
            str,
            Field(description="progress or failure"),
        ] = "progress",
        result: Annotated[
            str | None,
            Field(description="Outcome or error message"),
        ] = None,
        next_step: Annotated[
            str | None,
            Field(description="Recommended next step"),
        ] = None,
    ) -> str:
        """Log progress or failure entry."""
        if not project_id or not project_id.strip():
            return _json({"_v": "1.0", "error": "project_id is required"})
        if not action or not action.strip():
            return _json({"_v": "1.0", "error": "action is required"})

        s = await _init()
        mem = s["memory"]

        if type == "failure":
            entry = await mem.log_failure(
                project_id=project_id,
                action=action,
                result=result,
                next_step=next_step,
            )
        else:
            entry = await mem.log_progress(
                project_id=project_id,
                action=action,
                result=result,
                next_step=next_step,
            )

        return _json({
            "_v": "1.0",
            "id": entry.id,
            "project_id": entry.project_id,
            "type": entry.type,
            "action": entry.action,
        })

    # ── Experience Memory tools (3) ──────────────────────────

    @mcp.tool()
    async def eg_save(
        content: Annotated[str, Field(description="What was learned/discovered")],
        type: Annotated[
            str,
            Field(description="solution|pattern|decision|workaround|gotcha"),
        ],
        context: Annotated[
            str | None,
            Field(description="Situation when this was learned"),
        ] = None,
        confidence: Annotated[
            str,
            Field(description="high|medium|low — affects decay rate"),
        ] = "high",
        tags: Annotated[
            list[str] | None,
            Field(description="Tags for categorization"),
        ] = None,
    ) -> str:
        """Save experience with configurable decay."""
        if not content or not content.strip():
            return _json({"_v": "1.0", "error": "content is required"})

        s = await _init()
        try:
            exp = await s["experience"].save(
                content=content.strip(),
                type=type,
                context=context,
                confidence=confidence,
                tags=tags,
            )
        except ValueError as e:
            return _json({"_v": "1.0", "error": str(e)})

        return _json({
            "_v": "1.0",
            "id": exp.id,
            "type": exp.type,
            "confidence": exp.confidence,
            "decay_rate": round(exp.decay_rate, 6),
            "score": exp.score,
        })

    @mcp.tool()
    async def eg_memories(
        text: Annotated[
            str | None,
            Field(description="Full-text search query"),
        ] = None,
        type: Annotated[
            str | None,
            Field(description="Filter by experience type"),
        ] = None,
        min_relevance: Annotated[
            float,
            Field(
                description="Minimum relevance 0.0-1.0",
                ge=0.0,
                le=1.0,
            ),
        ] = 0.0,
        limit: Annotated[
            int,
            Field(description="Max results", ge=1, le=50),
        ] = 10,
        offset: Annotated[
            int,
            Field(description="Pagination offset", ge=0),
        ] = 0,
    ) -> str:
        """Decay-aware experience search."""
        s = await _init()
        experiences = await s["experience"].search(
            text=text,
            exp_type=type,
            min_relevance=min_relevance,
            limit=limit,
            offset=offset,
        )
        items = [
            {
                "id": e.id,
                "type": e.type,
                "content": e.content,
                "confidence": e.confidence,
                "relevance": round(e.relevance(), 4),
                "tags": e.tags,
            }
            for e in experiences
        ]
        return _json({"_v": "1.0", "count": len(items), "experiences": items})

    @mcp.tool()
    async def eg_prune(
        threshold: Annotated[
            float,
            Field(
                description="Remove experiences below this relevance",
                ge=0.0,
                le=1.0,
            ),
        ] = 0.01,
    ) -> str:
        """Remove expired experiences (archive first)."""
        s = await _init()
        pruned = await s["experience"].prune(threshold=threshold)
        return _json({
            "_v": "1.0",
            "pruned_count": len(pruned),
            "pruned_ids": pruned,
        })

    # ── Idea tools (2) ───────────────────────────────────────

    @mcp.tool()
    async def eg_idea(
        title: Annotated[str, Field(description="Idea title")],
        idea_id: Annotated[
            str | None,
            Field(description="Idea ID (omit to create new)"),
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Category classification"),
        ] = None,
        score: Annotated[
            float | None,
            Field(description="Numerical score"),
        ] = None,
        status: Annotated[
            str | None,
            Field(description="Status: draft|evaluating|approved|implementing|done|archived"),
        ] = None,
        link_to: Annotated[
            str | None,
            Field(description="Node ID to link this idea to"),
        ] = None,
    ) -> str:
        """Create or update idea with graph links."""
        if not title or not title.strip():
            return _json({"_v": "1.0", "error": "title is required"})

        s = await _init()
        ideas_engine = s["ideas"]

        if idea_id:
            # Update existing
            updates: dict[str, Any] = {"title": title.strip()}
            if category is not None:
                updates["category"] = category
            if score is not None:
                updates["score"] = score
            if status is not None:
                updates["status"] = status
            try:
                idea = await ideas_engine.update(idea_id, **updates)
            except ValueError as e:
                return _json({"_v": "1.0", "error": str(e)})
            if not idea:
                return _json({"_v": "1.0", "error": f"Idea not found: {idea_id}"})
        else:
            # Create new
            try:
                idea = await ideas_engine.create(
                    title=title.strip(),
                    category=category,
                    score=score,
                )
            except ValueError as e:
                return _json({"_v": "1.0", "error": str(e)})

        result: dict[str, Any] = {
            "_v": "1.0",
            "id": idea.id,
            "title": idea.title,
            "status": idea.status,
            "category": idea.category,
            "score": idea.score,
        }

        # Optional graph link
        if link_to:
            edge = await ideas_engine.link_to_node(idea.id, link_to)
            result["linked_to"] = link_to if edge else None
            if not edge:
                result["link_error"] = f"Node not found: {link_to}"

        return _json(result)

    @mcp.tool()
    async def eg_ideas(
        status: Annotated[
            str | None,
            Field(description="Filter by status"),
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Filter by category"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Max results", ge=1, le=50),
        ] = 10,
        offset: Annotated[
            int,
            Field(description="Pagination offset", ge=0),
        ] = 0,
    ) -> str:
        """List and filter ideas by status/score."""
        s = await _init()
        ideas_list = await s["ideas"].list_ideas(
            status=status,
            category=category,
            limit=limit,
            offset=offset,
        )
        items = [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "category": i.category,
                "score": i.score,
            }
            for i in ideas_list
        ]
        return _json({"_v": "1.0", "count": len(items), "ideas": items})

    # ── Resources (3) ──────────────────────────────────────────

    @mcp.resource("eg://status")
    async def eg_resource_status() -> str:
        """Graph and system overview."""
        s = await _init()
        stats = await s["graph"].stats()
        projects = await s["memory"].list_projects(active_only=True)
        active = projects[0] if projects else None
        return _json({
            "_v": "1.0",
            "graph": stats,
            "active_project": {
                "id": active.id,
                "name": active.name,
                "phase": active.phase,
            } if active else None,
        })

    @mcp.resource("eg://projects")
    async def eg_resource_projects() -> str:
        """All projects with progress summaries."""
        s = await _init()
        mem = s["memory"]
        projects = await mem.list_projects()
        items = []
        for p in projects:
            progress = await mem.get_progress(p.id, limit=3)
            items.append({
                "id": p.id,
                "name": p.name,
                "phase": p.phase,
                "active": p.active,
                "goals": p.goals,
                "recent_progress": [
                    {"action": e.action, "type": e.type}
                    for e in progress
                ],
            })
        return _json({"_v": "1.0", "count": len(items), "projects": items})

    @mcp.resource("eg://memories")
    async def eg_resource_memories() -> str:
        """Recent high-relevance experiences."""
        s = await _init()
        experiences = await s["experience"].search(
            min_relevance=0.1,
            limit=20,
        )
        items = [
            {
                "id": e.id,
                "type": e.type,
                "content": e.content[:200],
                "confidence": e.confidence,
                "relevance": round(e.relevance(), 4),
            }
            for e in experiences
        ]
        return _json({"_v": "1.0", "count": len(items), "experiences": items})

    # ── Prompts (2) ──────────────────────────────────────────

    @mcp.prompt()
    async def eg_bootup() -> str:
        """Session start — load active project, recent progress, and top memories."""
        s = await _init()
        mem = s["memory"]

        # Active project
        projects = await mem.list_projects(active_only=True)
        active = projects[0] if projects else None

        # Recent progress
        progress_lines = []
        if active:
            entries = await mem.get_progress(active.id, limit=5)
            for e in entries:
                prefix = "FAIL" if e.type == "failure" else "OK"
                progress_lines.append(f"  [{prefix}] {e.action}")

        # Top experiences
        experiences = await s["experience"].search(min_relevance=0.3, limit=5)
        memory_lines = [
            f"  [{e.type}] {e.content[:80]}"
            for e in experiences
        ]

        # Build context
        parts = ["# Engram Session Context\n"]

        if active:
            parts.append(f"## Active Project: {active.name}")
            parts.append(f"Phase: {active.phase}")
            if active.goals:
                parts.append("Goals: " + ", ".join(active.goals))
            if progress_lines:
                parts.append("\nRecent progress:")
                parts.extend(progress_lines)
        else:
            parts.append("No active project. Use eg_project to create one.")

        if memory_lines:
            parts.append("\n## Key Memories")
            parts.extend(memory_lines)

        # Ideas in progress
        ideas = await s["ideas"].list_ideas(status="implementing", limit=3)
        if ideas:
            parts.append("\n## Ideas in Progress")
            for idea in ideas:
                parts.append(f"  - {idea.title} ({idea.status})")

        return "\n".join(parts)

    @mcp.prompt()
    async def eg_review() -> str:
        """Session review — summarize what happened and suggest next steps."""
        s = await _init()
        mem = s["memory"]

        projects = await mem.list_projects(active_only=True)
        active = projects[0] if projects else None

        parts = ["# Session Review\n"]

        if active:
            parts.append(f"## Project: {active.name} ({active.phase})")

            # All progress this session (recent entries)
            progress = await mem.get_progress(active.id, limit=10)
            successes = [e for e in progress if e.type == "progress"]
            failures = [e for e in progress if e.type == "failure"]

            if successes:
                parts.append(f"\n### Completed ({len(successes)})")
                for e in successes:
                    parts.append(f"  - {e.action}")
                    if e.result:
                        parts.append(f"    Result: {e.result}")

            if failures:
                parts.append(f"\n### Issues ({len(failures)})")
                for e in failures:
                    parts.append(f"  - {e.action}")
                    if e.result:
                        parts.append(f"    Error: {e.result}")
                    if e.next_step:
                        parts.append(f"    Next: {e.next_step}")

            # Suggest next step from most recent entry
            if progress and progress[0].next_step:
                parts.append(f"\n## Suggested Next Step")
                parts.append(f"{progress[0].next_step}")
        else:
            parts.append("No active project to review.")

        # Experience stats
        all_exp = await s["experience"].search(limit=50)
        if all_exp:
            by_type: dict[str, int] = {}
            for e in all_exp:
                by_type[e.type] = by_type.get(e.type, 0) + 1
            parts.append("\n## Memory Stats")
            for t, count in sorted(by_type.items()):
                parts.append(f"  {t}: {count}")

        return "\n".join(parts)

    return mcp
