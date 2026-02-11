"""FastMCP server — 5 consolidated tools, 3 resources, 2 prompts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from kairn.core.experience import ExperienceEngine
from kairn.core.graph import GraphEngine
from kairn.core.ideas import IdeaEngine
from kairn.core.intelligence import IntelligenceLayer
from kairn.core.memory import ProjectMemory
from kairn.core.router import ContextRouter
from kairn.events.bus import EventBus
from kairn.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str)


def _ok(data: dict[str, Any]) -> str:
    """Return a versioned JSON success response."""
    return _json({**data, "_v": "1.0"})


def _err(msg: str) -> str:
    """Return a versioned JSON error response."""
    return _json({"_v": "1.0", "error": msg})


def create_server(db_path: str) -> FastMCP:
    """Create FastMCP server with 5 consolidated tools."""
    mcp = FastMCP("kairn", version="0.1.0")

    state: dict[str, Any] = {}
    _lock = asyncio.Lock()

    async def _init() -> dict[str, Any]:
        async with _lock:
            if "init_failed" in state:
                raise RuntimeError(f"Kairn init previously failed for {db_path}")
            if "graph" not in state:
                from pathlib import Path

                try:
                    store = SQLiteStore(Path(db_path))
                    await store.initialize()
                except Exception as e:
                    state["init_failed"] = True
                    logger.error("Failed to initialize database: %s", e)
                    raise RuntimeError(f"Kairn init failed: {db_path}") from e
                bus = EventBus()
                state["store"] = store
                state["bus"] = bus
                graph = GraphEngine(store, bus)
                router = ContextRouter(store, bus)
                memory = ProjectMemory(store, bus)
                experience = ExperienceEngine(store, bus)
                ideas = IdeaEngine(store, bus)
                state["graph"] = graph
                state["router"] = router
                state["memory"] = memory
                state["experience"] = experience
                state["ideas"] = ideas
                state["intel"] = IntelligenceLayer(
                    store=store,
                    event_bus=bus,
                    graph=graph,
                    router=router,
                    memory=memory,
                    experience=experience,
                    ideas=ideas,
                )
        return state

    # ── kn_graph ──────────────────────────────────────────────

    @mcp.tool()
    async def kn_graph(
        action: Annotated[
            Literal["add", "connect", "query", "remove", "status"],
            Field(description="add | connect | query | remove | status"),
        ],
        name: Annotated[
            str | None,
            Field(description="Node name (add)"),
        ] = None,
        type: Annotated[
            str | None,
            Field(description="Node type, e.g. concept, pattern (add)"),
        ] = None,
        namespace: Annotated[
            str | None,
            Field(description="Namespace (add: defaults to 'knowledge'; query: filter by namespace)"),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Node description (add)"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(description="Tags (add, query)"),
        ] = None,
        source_id: Annotated[
            str | None,
            Field(description="Source node ID (connect, remove)"),
        ] = None,
        target_id: Annotated[
            str | None,
            Field(description="Target node ID (connect, remove)"),
        ] = None,
        edge_type: Annotated[
            str | None,
            Field(description="Relationship type (connect, remove)"),
        ] = None,
        weight: Annotated[
            float,
            Field(description="Edge weight 0.0-1.0 (connect)", ge=0.0, le=1.0),
        ] = 1.0,
        node_id: Annotated[
            str | None,
            Field(description="Node ID to remove (remove)"),
        ] = None,
        text: Annotated[
            str | None,
            Field(description="Full-text search query (query)"),
        ] = None,
        node_type: Annotated[
            str | None,
            Field(description="Filter by node type (query)"),
        ] = None,
        detail: Annotated[
            str,
            Field(description="summary or full (query, default: summary)"),
        ] = "summary",
        limit: Annotated[
            int,
            Field(description="Max results 1-50 (query)", ge=1, le=50),
        ] = 10,
        offset: Annotated[
            int,
            Field(description="Pagination offset (query)", ge=0),
        ] = 0,
    ) -> str:
        """Direct operations on the knowledge graph: create, connect, search, and remove nodes and edges. Use for structured knowledge that should persist permanently. For storing knowledge learned during a conversation, prefer kn_intel (action="learn") which automatically decides storage strategy.

Actions: add (create node), connect (create edge), query (search nodes), remove (soft-delete node or edge), status (system health)."""  # noqa: E501
        s = await _init()

        if action == "add":
            if not name or not name.strip():
                return _err("name is required for add")
            if not type or not type.strip():
                return _err("type is required for add")
            node = await s["graph"].add_node(
                name=name.strip(),
                type=type.strip(),
                namespace=namespace or "knowledge",
                description=description,
                tags=tags,
            )
            await s["router"].update_routes_for_node(
                node.id, node.name, node.description,
            )
            return _ok(node.to_response(detail="full"))

        if action == "connect":
            if not source_id or not source_id.strip():
                return _err("source_id is required for connect")
            if not target_id or not target_id.strip():
                return _err("target_id is required for connect")
            if not edge_type or not edge_type.strip():
                return _err("edge_type is required for connect")
            try:
                edge = await s["graph"].connect(
                    source_id.strip(), target_id.strip(), edge_type.strip(),
                    weight=weight,
                )
                return _ok(edge.to_storage())
            except ValueError as e:
                return _err(str(e))

        if action == "query":
            nodes = await s["graph"].query(
                text=text,
                namespace=namespace,
                node_type=node_type,
                tags=tags,
                limit=limit,
                offset=offset,
            )
            items = [n.to_response(detail=detail) for n in nodes]
            return _ok({"count": len(items), "nodes": items})

        if action == "remove":
            if node_id and node_id.strip():
                ok = await s["graph"].remove_node(node_id.strip())
                if ok:
                    return _ok({"removed": "node", "id": node_id.strip()})
                return _err(f"Node not found: {node_id}")

            src = source_id.strip() if source_id else None
            tgt = target_id.strip() if target_id else None
            etype = edge_type.strip() if edge_type else None

            if src and tgt and etype:
                ok = await s["graph"].disconnect(src, tgt, etype)
                if ok:
                    return _ok({
                        "removed": "edge",
                        "source_id": src,
                        "target_id": tgt,
                    })
                return _err("Edge not found")

            return _err("Provide node_id or (source_id + target_id + edge_type)")

        if action == "status":
            stats = await s["graph"].stats()
            return _ok(stats)

        return _err(f"Unknown action: {action}")

    # ── kn_project ────────────────────────────────────────────

    @mcp.tool()
    async def kn_project(
        action: Annotated[
            Literal["create", "update", "list", "log"],
            Field(description="create | update | list | log"),
        ],
        name: Annotated[
            str | None,
            Field(description="Project name (create, update)"),
        ] = None,
        project_id: Annotated[
            str | None,
            Field(description="Existing project ID (update, log)"),
        ] = None,
        phase: Annotated[
            str | None,
            Field(description="Phase: planning|active|paused|done (update)"),
        ] = None,
        goals: Annotated[
            list[str] | None,
            Field(description="Project goals (create, update)"),
        ] = None,
        stakeholders: Annotated[
            list[str] | None,
            Field(description="Stakeholders (create, update)"),
        ] = None,
        success_metrics: Annotated[
            list[str] | None,
            Field(description="Success metrics / KPIs (create, update)"),
        ] = None,
        active_only: Annotated[
            bool,
            Field(description="Only show active projects (list)"),
        ] = False,
        set_active: Annotated[
            str | None,
            Field(description="Project ID to set as active (list)"),
        ] = None,
        action_text: Annotated[
            str | None,
            Field(description="What was done or what failed (log)"),
        ] = None,
        type: Annotated[
            str,
            Field(description="progress or failure (log, default: progress)"),
        ] = "progress",
        result: Annotated[
            str | None,
            Field(description="Outcome or error message (log)"),
        ] = None,
        next_step: Annotated[
            str | None,
            Field(description="Recommended next step (log)"),
        ] = None,
    ) -> str:
        """Manage projects and log session activity. Projects track goals, phases, and progress over time. Use action="log" to record what was accomplished or failed — this builds the history that kn_bootup and kn_review use for continuity across sessions.

Actions: create (new project), update (modify existing), list (show projects), log (record progress/failure entry)."""  # noqa: E501
        s = await _init()
        mem = s["memory"]

        if action == "create":
            if not name or not name.strip():
                return _err("name is required for create")
            if phase is not None:
                return _err("phase cannot be set on create (starts at planning)")
            try:
                project = await mem.create_project(
                    name=name.strip(),
                    goals=goals,
                    stakeholders=stakeholders,
                    success_metrics=success_metrics,
                )
            except ValueError as e:
                return _err(str(e))
            return _ok({
                "id": project.id,
                "name": project.name,
                "phase": project.phase,
                "active": project.active,
                "goals": project.goals,
            })

        if action == "update":
            if not project_id:
                return _err("project_id is required for update")
            if not name or not name.strip():
                return _err("name is required for update")
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
                return _err(str(e))
            if not project:
                return _err(f"Project not found: {project_id}")
            return _ok({
                "id": project.id,
                "name": project.name,
                "phase": project.phase,
                "active": project.active,
                "goals": project.goals,
            })

        if action == "list":
            if set_active:
                ok = await mem.set_active_project(set_active)
                if not ok:
                    return _err(f"Project not found: {set_active}")

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
            return _ok({"count": len(items), "projects": items})

        if action == "log":
            if not project_id or not project_id.strip():
                return _err("project_id is required for log")
            if not action_text or not action_text.strip():
                return _err("action_text is required for log")

            if type == "failure":
                entry = await mem.log_failure(
                    project_id=project_id,
                    action=action_text,
                    result=result,
                    next_step=next_step,
                )
            else:
                entry = await mem.log_progress(
                    project_id=project_id,
                    action=action_text,
                    result=result,
                    next_step=next_step,
                )
            return _ok({
                "id": entry.id,
                "project_id": entry.project_id,
                "type": entry.type,
                "action": entry.action,
            })

        return _err(f"Unknown action: {action}")

    # ── kn_experience ─────────────────────────────────────────

    @mcp.tool()
    async def kn_experience(
        action: Annotated[
            Literal["save", "search", "prune"],
            Field(description="save | search | prune"),
        ],
        content: Annotated[
            str | None,
            Field(description="What was learned or discovered (save)"),
        ] = None,
        type: Annotated[
            str | None,
            Field(description="solution|pattern|decision|workaround|gotcha (save, search)"),
        ] = None,
        context: Annotated[
            str | None,
            Field(description="Situation when this was learned (save)"),
        ] = None,
        confidence: Annotated[
            str,
            Field(description="high|medium|low — lower decays faster (save, default: high)"),
        ] = "high",
        tags: Annotated[
            list[str] | None,
            Field(description="Tags for categorization (save)"),
        ] = None,
        text: Annotated[
            str | None,
            Field(description="Full-text search query (search)"),
        ] = None,
        min_relevance: Annotated[
            float,
            Field(description="Minimum relevance 0.0-1.0 (search)", ge=0.0, le=1.0),
        ] = 0.0,
        limit: Annotated[
            int,
            Field(description="Max results 1-50 (search)", ge=1, le=50),
        ] = 10,
        offset: Annotated[
            int,
            Field(description="Pagination offset (search)", ge=0),
        ] = 0,
        threshold: Annotated[
            float,
            Field(description="Remove below this relevance (prune, default: 0.01)", ge=0.0, le=1.0),
        ] = 0.01,
    ) -> str:
        """Store and retrieve experiential memories that decay over time. Unlike permanent graph nodes, experiences lose relevance based on type and confidence — workarounds fade fastest, patterns persist longest. For the common case of saving something learned in conversation, prefer kn_intel (action="learn") which chooses storage automatically.

Actions: save (store experience), search (find past experiences by relevance), prune (remove decayed experiences)."""  # noqa: E501
        s = await _init()
        exp_engine = s["experience"]

        if action == "save":
            if not content or not content.strip():
                return _err("content is required for save")
            if not type:
                return _err("type is required for save")
            try:
                exp = await exp_engine.save(
                    content=content.strip(),
                    type=type,
                    context=context,
                    confidence=confidence,
                    tags=tags,
                )
            except ValueError as e:
                return _err(str(e))
            return _ok({
                "id": exp.id,
                "type": exp.type,
                "confidence": exp.confidence,
                "decay_rate": round(exp.decay_rate, 6),
                "score": exp.score,
            })

        if action == "search":
            experiences = await exp_engine.search(
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
            return _ok({"count": len(items), "experiences": items})

        if action == "prune":
            pruned = await exp_engine.prune(threshold=threshold)
            return _ok({"pruned_count": len(pruned), "pruned_ids": pruned})

        return _err(f"Unknown action: {action}")

    # ── kn_idea ───────────────────────────────────────────────

    @mcp.tool()
    async def kn_idea(
        action: Annotated[
            Literal["create", "update", "list"],
            Field(description="create | update | list"),
        ],
        title: Annotated[
            str | None,
            Field(description="Idea title (create, update)"),
        ] = None,
        idea_id: Annotated[
            str | None,
            Field(description="Existing idea ID (update)"),
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Category classification (create, update, list)"),
        ] = None,
        score: Annotated[
            float | None,
            Field(description="Numerical score (create, update)"),
        ] = None,
        status: Annotated[
            str | None,
            Field(description="draft|evaluating|approved|implementing|done|archived (update, list)"),
        ] = None,
        link_to: Annotated[
            str | None,
            Field(description="Node ID to link this idea to (create, update)"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Max results 1-50 (list)", ge=1, le=50),
        ] = 10,
        offset: Annotated[
            int,
            Field(description="Pagination offset (list)", ge=0),
        ] = 0,
    ) -> str:
        """Capture and track ideas through a lifecycle: draft, evaluating, approved, implementing, done, archived. Ideas can be scored, categorized, and linked to knowledge graph nodes.

Actions: create (new idea), update (modify existing), list (filter ideas)."""  # noqa: E501
        s = await _init()
        ideas_engine = s["ideas"]

        if action == "create":
            if not title or not title.strip():
                return _err("title is required for create")
            try:
                idea = await ideas_engine.create(
                    title=title.strip(),
                    category=category,
                    score=score,
                )
            except ValueError as e:
                return _err(str(e))

            result_data: dict[str, Any] = {
                "id": idea.id,
                "title": idea.title,
                "status": idea.status,
                "category": idea.category,
                "score": idea.score,
            }
            if link_to:
                edge = await ideas_engine.link_to_node(idea.id, link_to)
                result_data["linked_to"] = link_to if edge else None
                if not edge:
                    result_data["link_error"] = f"Node not found: {link_to}"
            return _ok(result_data)

        if action == "update":
            if not idea_id:
                return _err("idea_id is required for update")
            if not title or not title.strip():
                return _err("title is required for update")
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
                return _err(str(e))
            if not idea:
                return _err(f"Idea not found: {idea_id}")

            result_data = {
                "id": idea.id,
                "title": idea.title,
                "status": idea.status,
                "category": idea.category,
                "score": idea.score,
            }
            if link_to:
                edge = await ideas_engine.link_to_node(idea.id, link_to)
                result_data["linked_to"] = link_to if edge else None
                if not edge:
                    result_data["link_error"] = f"Node not found: {link_to}"
            return _ok(result_data)

        if action == "list":
            ideas_list = await ideas_engine.list_ideas(
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
            return _ok({"count": len(items), "ideas": items})

        return _err(f"Unknown action: {action}")

    # ── kn_intel ──────────────────────────────────────────────

    @mcp.tool()
    async def kn_intel(
        action: Annotated[
            Literal["learn", "recall", "crossref", "context", "related"],
            Field(description="learn | recall | crossref | context | related"),
        ],
        content: Annotated[
            str | None,
            Field(description="What was learned/decided/discovered (learn)"),
        ] = None,
        type: Annotated[
            str | None,
            Field(description="decision|pattern|solution|workaround|gotcha (learn)"),
        ] = None,
        context: Annotated[
            str | None,
            Field(description="Situation when this was learned (learn)"),
        ] = None,
        confidence: Annotated[
            str,
            Field(
                description="high = permanent node + experience, medium/low = decaying experience only (learn, default: high)"
            ),
        ] = "high",
        tags: Annotated[
            list[str] | None,
            Field(description="Tags for categorization (learn)"),
        ] = None,
        topic: Annotated[
            str | None,
            Field(description="Topic to recall knowledge about (recall)"),
        ] = None,
        problem: Annotated[
            str | None,
            Field(description="Problem description to find solutions for (crossref)"),
        ] = None,
        keywords: Annotated[
            str | None,
            Field(description="Keywords to find relevant context for (context)"),
        ] = None,
        detail: Annotated[
            str,
            Field(description="summary or full (context, default: summary)"),
        ] = "summary",
        node_id: Annotated[
            str | None,
            Field(description="Starting node ID (related)"),
        ] = None,
        depth: Annotated[
            int,
            Field(description="Traversal depth 1-5 (related, default: 1)", ge=1, le=5),
        ] = 1,
        edge_type: Annotated[
            str | None,
            Field(description="Filter by edge type (related)"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Max results 1-50 (recall, crossref, context, related)", ge=1, le=50),
        ] = 10,
        min_relevance: Annotated[
            float,
            Field(description="Minimum relevance 0.0-1.0 (recall)", ge=0.0, le=1.0),
        ] = 0.0,
    ) -> str:
        """The primary interface for storing and retrieving knowledge. Combines graph, experience memory, and routing to handle knowledge intelligently. Use as the default for learning or recalling — it routes by confidence and type automatically. Use kn_graph, kn_experience, or kn_idea only when you need direct control.

Actions: learn (store from conversation), recall (surface past knowledge), crossref (find solutions across workspaces), context (keywords to subgraph), related (graph traversal from a node)."""  # noqa: E501
        s = await _init()
        intel = s["intel"]

        if action == "learn":
            if not content or not content.strip():
                return _err("content is required for learn")
            if not type:
                return _err("type is required for learn")
            try:
                result = await intel.learn(
                    content=content.strip(),
                    type=type,
                    context=context,
                    confidence=confidence,
                    tags=tags,
                )
            except ValueError as e:
                return _err(str(e))
            return _json(result)

        if action == "recall":
            results = await intel.recall(
                topic=topic,
                limit=limit,
                min_relevance=min_relevance,
            )
            return _ok({"count": len(results), "results": results})

        if action == "crossref":
            if not problem or not problem.strip():
                return _err("problem is required for crossref")
            try:
                results = await intel.crossref(
                    problem=problem.strip(),
                    limit=limit,
                )
            except ValueError as e:
                return _err(str(e))
            return _ok({"count": len(results), "results": results})

        if action == "context":
            if not keywords or not keywords.strip():
                return _err("keywords is required for context")
            result = await intel.context(
                keywords=keywords.strip(),
                detail=detail,
                limit=limit,
            )
            return _json(result)

        if action == "related":
            if not node_id or not node_id.strip():
                return _err("node_id is required for related")
            results = await intel.related(
                node_id=node_id.strip(),
                depth=depth,
                edge_type=edge_type,
            )
            return _ok({"count": len(results), "results": results})

        return _err(f"Unknown action: {action}")

    # ── Resources (3) ──────────────────────────────────────────

    @mcp.resource("kn://status")
    async def kn_resource_status() -> str:
        """Graph and system overview."""
        s = await _init()
        stats = await s["graph"].stats()
        projects = await s["memory"].list_projects(active_only=True)
        active = projects[0] if projects else None
        return _ok({
            "graph": stats,
            "active_project": {
                "id": active.id,
                "name": active.name,
                "phase": active.phase,
            }
            if active
            else None,
        })

    @mcp.resource("kn://projects")
    async def kn_resource_projects() -> str:
        """All projects with progress summaries."""
        s = await _init()
        mem = s["memory"]
        projects = await mem.list_projects()
        items = []
        for p in projects:
            progress = await mem.get_progress(p.id, limit=3)
            items.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "phase": p.phase,
                    "active": p.active,
                    "goals": p.goals,
                    "recent_progress": [{"action": e.action, "type": e.type} for e in progress],
                }
            )
        return _ok({"count": len(items), "projects": items})

    @mcp.resource("kn://memories")
    async def kn_resource_memories() -> str:
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
        return _ok({"count": len(items), "experiences": items})

    # ── Prompts (2) ──────────────────────────────────────────

    @mcp.prompt()
    async def kn_bootup() -> str:
        """Session start — load active project, recent progress, and top memories."""
        s = await _init()
        mem = s["memory"]

        projects = await mem.list_projects(active_only=True)
        active = projects[0] if projects else None

        progress_lines = []
        if active:
            entries = await mem.get_progress(active.id, limit=5)
            for e in entries:
                prefix = "FAIL" if e.type == "failure" else "OK"
                progress_lines.append(f"  [{prefix}] {e.action}")

        experiences = await s["experience"].search(min_relevance=0.3, limit=5)
        memory_lines = [f"  [{e.type}] {e.content[:80]}" for e in experiences]

        parts = ["# Kairn Session Context\n"]

        if active:
            parts.append(f"## Active Project: {active.name}")
            parts.append(f"Phase: {active.phase}")
            if active.goals:
                parts.append("Goals: " + ", ".join(active.goals))
            if progress_lines:
                parts.append("\nRecent progress:")
                parts.extend(progress_lines)
        else:
            parts.append("No active project. Use kn_project(action=\"create\") to create one.")

        if memory_lines:
            parts.append("\n## Key Memories")
            parts.extend(memory_lines)

        ideas = await s["ideas"].list_ideas(status="implementing", limit=3)
        if ideas:
            parts.append("\n## Ideas in Progress")
            for idea in ideas:
                parts.append(f"  - {idea.title} ({idea.status})")

        return "\n".join(parts)

    @mcp.prompt()
    async def kn_review() -> str:
        """Session review — summarize what happened and suggest next steps."""
        s = await _init()
        mem = s["memory"]

        projects = await mem.list_projects(active_only=True)
        active = projects[0] if projects else None

        parts = ["# Session Review\n"]

        if active:
            parts.append(f"## Project: {active.name} ({active.phase})")

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

            if progress and progress[0].next_step:
                parts.append("\n## Suggested Next Step")
                parts.append(f"{progress[0].next_step}")
        else:
            parts.append("No active project to review.")

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
