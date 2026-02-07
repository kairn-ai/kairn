"""Interactive demo showcasing kairn's learn→recall→crossref→context workflow.

Walks through creating knowledge nodes, experiences, projects, and using the
intelligence layer to demonstrate the core kairn capabilities.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from kairn.core.experience import ExperienceEngine
from kairn.core.graph import GraphEngine
from kairn.core.ideas import IdeaEngine
from kairn.core.intelligence import IntelligenceLayer
from kairn.core.memory import ProjectMemory
from kairn.core.router import ContextRouter
from kairn.events.bus import EventBus
from kairn.storage.sqlite_store import SQLiteStore

console = Console()


def step_header(num: int, title: str) -> None:
    """Display a colorful step header."""
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Step {num}:[/bold cyan] [yellow]{title}[/yellow]",
            border_style="cyan",
        )
    )


def display_json(data: dict | list, title: str | None = None) -> None:
    """Display JSON data in a panel."""
    json_str = json.dumps(data, indent=2)
    if title:
        console.print(Panel(JSON(json_str), title=title, border_style="green"))
    else:
        console.print(Panel(JSON(json_str), border_style="green"))


async def demo() -> None:
    """Run the interactive demo."""
    console.print(
        "[bold magenta]╔═══════════════════════════════════════════════════╗[/bold magenta]"
    )
    console.print(
        "[bold magenta]║[/bold magenta] [bold white]KAIRN DEMO: "
        "Learn → Recall → Crossref → Context[/bold white] "
        "[bold magenta]║[/bold magenta]"
    )
    console.print(
        "[bold magenta]╚═══════════════════════════════════════════════════╝[/bold magenta]"
    )
    console.print(
        "\n[dim]This demo creates a temporary workspace and walks through\n"
        "the core kairn workflow using an e-commerce API project.[/dim]\n"
    )

    # Create temporary workspace
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "kairn.db"
    console.print(f"[dim]Workspace: {db_path}[/dim]\n")

    # Initialize kairn components
    store = SQLiteStore(db_path)
    await store.initialize()
    bus = EventBus()

    graph = GraphEngine(store, bus)
    router = ContextRouter(store, bus)
    memory = ProjectMemory(store, bus)
    experience = ExperienceEngine(store, bus)
    ideas = IdeaEngine(store, bus)
    intelligence = IntelligenceLayer(
        store=store,
        event_bus=bus,
        graph=graph,
        router=router,
        memory=memory,
        experience=experience,
        ideas=ideas,
    )

    # Step 1: Add knowledge nodes
    step_header(1, "Creating Knowledge Nodes")
    console.print("[dim]Adding nodes about e-commerce API architecture...[/dim]\n")

    node1 = await graph.add_node(
        name="JWT Authentication Pattern",
        type="auth",
        namespace="knowledge",
        description=(
            "Use JWT tokens with Redis-backed refresh tokens. "
            "Access tokens expire in 15min, refresh tokens in 7 days."
        ),
        tags=["authentication", "security", "jwt"],
    )
    console.print(f"[green]✓[/green] Created node: {node1.name}")

    node2 = await graph.add_node(
        name="Token Bucket Rate Limiting",
        type="rate_limiting",
        namespace="knowledge",
        description=(
            "Implement token bucket algorithm: 100 requests per minute per user, "
            "with burst capacity of 120."
        ),
        tags=["rate-limiting", "performance"],
    )
    console.print(f"[green]✓[/green] Created node: {node2.name}")

    node3 = await graph.add_node(
        name="PostgreSQL Product Schema",
        type="database",
        namespace="knowledge",
        description=(
            "Products table with JSONB for flexible attributes. "
            "Use GIN index on attributes column for fast queries."
        ),
        tags=["postgresql", "schema", "database"],
    )
    console.print(f"[green]✓[/green] Created node: {node3.name}")

    node4 = await graph.add_node(
        name="Redis Caching Strategy",
        type="caching",
        namespace="knowledge",
        description=(
            "Cache product catalog with 1-hour TTL. Invalidate on update using pub/sub pattern."
        ),
        tags=["redis", "caching", "performance"],
    )
    console.print(f"[green]✓[/green] Created node: {node4.name}")

    # Step 2: Connect nodes
    step_header(2, "Connecting Knowledge Graph")
    console.print("[dim]Creating relationships between concepts...[/dim]\n")

    await graph.connect(
        node1.id,
        node4.id,
        "uses",
        weight=0.9,
        properties={"reason": "JWT session data stored in Redis"},
    )
    console.print("[green]✓[/green] Connected: JWT → Redis")

    await graph.connect(
        node3.id,
        node4.id,
        "cached_by",
        weight=0.85,
        properties={"cache_strategy": "write-through"},
    )
    console.print("[green]✓[/green] Connected: PostgreSQL → Redis")

    await graph.connect(
        node2.id,
        node4.id,
        "depends_on",
        weight=0.8,
        properties={"reason": "Rate limit counters stored in Redis"},
    )
    console.print("[green]✓[/green] Connected: Rate Limiting → Redis")

    # Step 3: Query the graph
    step_header(3, "Searching Knowledge Graph (FTS5)")
    console.print("[dim]Searching for 'redis caching performance'...[/dim]\n")

    results = await graph.query(text="redis caching performance", limit=3)
    table = Table(title="Search Results", show_lines=True)
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Tags", style="green")

    for node in results:
        table.add_row(node.name, node.type, ", ".join(node.tags or []))

    console.print(table)

    # Step 4: Save experiences
    step_header(4, "Saving Experiences with Decay")
    console.print(
        "[dim]Recording solutions and patterns with different confidence levels...[/dim]\n"
    )

    exp1 = await experience.save(
        content=(
            "Token bucket rate limiting solved the API throttling issue. "
            "Implementation took 3 hours."
        ),
        type="solution",
        context="API Gateway redesign sprint",
        confidence="high",
        tags=["rate-limiting", "api-gateway"],
    )
    console.print(f"[green]✓[/green] Saved solution (high confidence): {exp1.id[:8]}...")

    exp2 = await experience.save(
        content=(
            "Repository pattern with UoW for database access "
            "keeps business logic clean and testable."
        ),
        type="pattern",
        context="Code review feedback",
        confidence="high",
        tags=["architecture", "database"],
    )
    console.print(f"[green]✓[/green] Saved pattern (high confidence): {exp2.id[:8]}...")

    exp3 = await experience.save(
        content="Considered using GraphQL but decided against it due to team's REST expertise.",
        type="decision",
        context="Architecture planning",
        confidence="medium",
        tags=["graphql", "rest", "api"],
    )
    console.print(f"[green]✓[/green] Saved decision (medium confidence): {exp3.id[:8]}...")

    # Step 5: Search memories
    step_header(5, "Searching Experiences (Decay-Aware)")
    console.print("[dim]Searching for 'rate limiting API'...[/dim]\n")

    exp_results = await experience.search(
        text="rate limiting API",
        min_relevance=0.1,
        limit=3,
    )

    exp_table = Table(title="Experience Results", show_lines=True)
    exp_table.add_column("Type", style="cyan")
    exp_table.add_column("Content", style="white", max_width=50)
    exp_table.add_column("Confidence", style="yellow")
    exp_table.add_column("Tags", style="green")

    for exp in exp_results:
        exp_table.add_row(
            exp.type,
            exp.content[:100] + "..." if len(exp.content) > 100 else exp.content,
            exp.confidence,
            ", ".join(exp.tags or []),
        )

    console.print(exp_table)

    # Step 6: Create project and log progress
    step_header(6, "Project Memory Tracking")
    console.print("[dim]Creating project and logging progress...[/dim]\n")

    project = await memory.create_project(
        name="E-Commerce API v2",
        goals=[
            "Implement JWT authentication",
            "Add rate limiting",
            "Optimize database queries",
        ],
        stakeholders=["Backend Team", "Product Manager"],
        success_metrics=["<100ms p95 latency", ">99.9% uptime"],
    )
    console.print(f"[green]✓[/green] Created project: {project.name}")

    await memory.log_progress(
        project_id=project.id,
        action="Implemented JWT authentication with Redis",
        result="Auth endpoints working, tests passing",
        next_step="Add rate limiting middleware",
    )
    console.print("[green]✓[/green] Logged progress entry")

    await memory.log_progress(
        project_id=project.id,
        action="Added token bucket rate limiting",
        result="Rate limiting active for all endpoints",
        next_step="Optimize database queries with Redis caching",
    )
    console.print("[green]✓[/green] Logged progress entry")

    # Step 7: Create an idea
    step_header(7, "Idea Lifecycle")
    console.print("[dim]Creating a new idea...[/dim]\n")

    idea = await ideas.create(
        title="Migrate to GraphQL for better mobile performance",
        category="architecture",
        score=7.5,
        properties={
            "estimated_effort": "2 sprints",
            "impact": "high",
            "complexity": "medium",
        },
    )
    console.print(f"[green]✓[/green] Created idea: {idea.title}")
    console.print(f"    Status: {idea.status}, Score: {idea.score}")

    # Step 8: Intelligence Layer - the main event
    step_header(8, "Intelligence Layer: Learn → Recall → Crossref → Context")

    # Learn
    console.print("\n[bold]8.1 Learn[/bold] - Store new knowledge")
    console.print("[dim]Teaching kairn about a new deployment pattern...[/dim]\n")

    learn_result = await intelligence.learn(
        content="Blue-green deployment with automated rollback reduces downtime to <1 second.",
        type="pattern",
        context="DevOps improvement initiative",
        confidence="high",
        tags=["deployment", "devops", "reliability"],
    )
    display_json(learn_result, "Learn Result")

    # Recall
    console.print("\n[bold]8.2 Recall[/bold] - Surface relevant past knowledge")
    console.print("[dim]Recalling knowledge about 'authentication security'...[/dim]\n")

    recall_results = await intelligence.recall(
        topic="authentication security",
        limit=3,
    )
    display_json(recall_results, "Recall Results")

    # Crossref
    console.print("\n[bold]8.3 Crossref[/bold] - Find similar solutions from workspace")
    console.print("[dim]Looking for solutions to 'slow API response times'...[/dim]\n")

    crossref_results = await intelligence.crossref(
        problem="slow API response times",
        limit=3,
    )
    display_json(crossref_results, "Crossref Results")

    # Context
    console.print(
        "\n[bold]8.4 Context[/bold] - Get relevant context subgraph with progressive disclosure"
    )
    console.print("[dim]Fetching context for 'redis performance caching'...[/dim]\n")

    context_summary = await intelligence.context(
        keywords="redis performance caching",
        detail="summary",
        limit=3,
    )
    display_json(context_summary, "Context (Summary)")

    console.print("\n[dim]Now with full details...[/dim]\n")
    context_full = await intelligence.context(
        keywords="redis performance caching",
        detail="full",
        limit=3,
    )
    display_json(context_full, "Context (Full)")

    # Related
    console.print("\n[bold]8.5 Related[/bold] - Find connected nodes via graph traversal")
    console.print("[dim]Finding nodes related to Redis caching...[/dim]\n")

    related_results = await intelligence.related(
        node_id=node4.id,
        depth=1,
    )
    display_json(related_results, "Related Nodes")

    # Step 9: Show stats
    step_header(9, "Workspace Statistics")
    stats = await graph.stats()

    stats_table = Table(title="Knowledge Graph Stats", show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="yellow")

    stats_table.add_row("Total Nodes", str(stats["total_nodes"]))
    stats_table.add_row("Total Edges", str(stats["total_edges"]))
    stats_table.add_row("Avg Edges/Node", f"{stats['avg_edges_per_node']:.2f}")

    console.print(stats_table)

    # Namespace breakdown
    namespace_table = Table(title="Nodes by Namespace", show_lines=True)
    namespace_table.add_column("Namespace", style="cyan")
    namespace_table.add_column("Count", style="yellow")

    for ns, count in stats["nodes_by_namespace"].items():
        namespace_table.add_row(ns, str(count))

    console.print(namespace_table)

    # Cleanup
    await store.close()

    console.print(
        "\n[bold green]✓ Demo complete![/bold green] "
        "[dim]Temporary workspace will be cleaned up.[/dim]\n"
    )
    console.print(
        "[dim]To create a persistent workspace, run: "
        "python examples/sample-workspace/create_sample.py[/dim]"
    )


if __name__ == "__main__":
    asyncio.run(demo())
