"""Create a pre-populated sample workspace for engram.

Generates engram.db with realistic developer knowledge covering:
- 20 nodes across knowledge/idea/project namespaces
- 15 edges connecting related concepts
- 10 experiences with varied confidence levels
- 3 projects in different phases
- 5 ideas with different statuses

Run: python examples/sample-workspace/create_sample.py
"""

import asyncio
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from engram.core.experience import ExperienceEngine
from engram.core.graph import GraphEngine
from engram.core.ideas import IdeaEngine
from engram.core.memory import ProjectMemory
from engram.events.bus import EventBus
from engram.storage.sqlite_store import SQLiteStore

console = Console()


async def create_sample_workspace() -> None:
    """Create sample workspace with realistic developer knowledge."""
    workspace_dir = Path(__file__).parent
    db_path = workspace_dir / "engram.db"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        console.print("[yellow]Removed existing database[/yellow]")

    console.print(f"\n[bold cyan]Creating sample workspace:[/bold cyan] {db_path}\n")

    # Initialize engram
    store = SQLiteStore(db_path)
    await store.initialize()
    bus = EventBus()

    graph = GraphEngine(store, bus)
    memory = ProjectMemory(store, bus)
    experience = ExperienceEngine(store, bus)
    ideas = IdeaEngine(store, bus)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create nodes
        task = progress.add_task("Creating knowledge nodes...", total=None)

        # Auth & Security nodes
        auth_jwt = await graph.add_node(
            name="JWT Authentication Pattern",
            type="auth_pattern",
            namespace="knowledge",
            description=(
                "Stateless authentication using JWT tokens. "
                "Access tokens expire in 15min, refresh tokens in 7 days. "
                "Store refresh tokens in Redis with automatic cleanup."
            ),
            tags=["authentication", "jwt", "security"],
        )

        auth_oauth = await graph.add_node(
            name="OAuth2 Social Login",
            type="auth_pattern",
            namespace="knowledge",
            description=(
                "Implement OAuth2 for Google and GitHub login. "
                "Use passport.js for Node.js or Authlib for Python. "
                "Handle state parameter for CSRF protection."
            ),
            tags=["authentication", "oauth2", "social-login"],
        )

        auth_rbac = await graph.add_node(
            name="Role-Based Access Control",
            type="security",
            namespace="knowledge",
            description=(
                "RBAC with roles (admin, editor, viewer) and permissions. "
                "Use middleware to check permissions before controller execution."
            ),
            tags=["authorization", "rbac", "security"],
        )

        auth_rate = await graph.add_node(
            name="Token Bucket Rate Limiting",
            type="rate_limiting",
            namespace="knowledge",
            description=(
                "Token bucket algorithm: 100 req/min per user with burst capacity of 120. "
                "Use Redis for distributed rate limiting across multiple servers."
            ),
            tags=["rate-limiting", "security", "performance"],
        )

        await graph.add_node(
            name="Password Hashing Best Practices",
            type="security",
            namespace="knowledge",
            description=(
                "Use Argon2id for password hashing (winner of Password Hashing Competition). "
                "bcrypt is acceptable fallback. Never use SHA256 or MD5 for passwords."
            ),
            tags=["security", "cryptography", "passwords"],
        )

        # Database & Performance nodes
        db_postgres = await graph.add_node(
            name="PostgreSQL JSONB Indexing",
            type="database",
            namespace="knowledge",
            description=(
                "JSONB columns with GIN indexes for fast queries. "
                "Use expression indexes for frequently accessed keys: "
                "CREATE INDEX ON table USING GIN ((data->'attribute'));"
            ),
            tags=["postgresql", "performance", "indexing"],
        )

        db_redis = await graph.add_node(
            name="Redis Caching Strategy",
            type="caching",
            namespace="knowledge",
            description=(
                "Cache-aside pattern with 1-hour TTL for frequently accessed data. "
                "Use Redis pub/sub for cache invalidation across instances."
            ),
            tags=["redis", "caching", "performance"],
        )

        db_pool = await graph.add_node(
            name="Connection Pooling Configuration",
            type="database",
            namespace="knowledge",
            description=(
                "Pool size = (CPU cores * 2) + effective_spindle_count. "
                "Min connections = pool_size / 2. "
                "Max lifetime = 30 minutes to handle idle connection cleanup."
            ),
            tags=["database", "performance", "configuration"],
        )

        db_migration = await graph.add_node(
            name="Zero-Downtime Database Migrations",
            type="deployment",
            namespace="knowledge",
            description=(
                "Backward-compatible migrations: add before remove, expand before contract. "
                "Use feature flags for schema changes affecting application logic."
            ),
            tags=["database", "migrations", "deployment"],
        )

        db_query = await graph.add_node(
            name="N+1 Query Prevention",
            type="performance",
            namespace="knowledge",
            description=(
                "Use eager loading (JOIN or IN queries) instead of lazy loading. "
                "ORMs: use select_related/prefetch_related (Django) or joinedload (SQLAlchemy)."
            ),
            tags=["database", "performance", "optimization"],
        )

        db_partition = await graph.add_node(
            name="Table Partitioning Strategy",
            type="database",
            namespace="knowledge",
            description=(
                "Partition by date range for time-series data. "
                "Use LIST partitioning for categorical data. "
                "Keep partition size under 100GB for optimal performance."
            ),
            tags=["postgresql", "scalability", "partitioning"],
        )

        # API Design nodes
        api_rest = await graph.add_node(
            name="RESTful API Design Principles",
            type="api_design",
            namespace="knowledge",
            description=(
                "Use HTTP verbs correctly: GET (read), POST (create), "
                "PUT/PATCH (update), DELETE (remove). "
                "Return 201 for creation, 204 for no content, 400 for validation errors."
            ),
            tags=["api", "rest", "design"],
        )

        await graph.add_node(
            name="API Versioning Strategies",
            type="api_design",
            namespace="knowledge",
            description=(
                "URL versioning (/v1/, /v2/) is most common and explicit. "
                "Header versioning (Accept: application/vnd.api.v2+json) "
                "is more RESTful but less visible."
            ),
            tags=["api", "versioning", "design"],
        )

        api_pagination = await graph.add_node(
            name="Cursor-Based Pagination",
            type="api_design",
            namespace="knowledge",
            description=(
                "Use cursor pagination for large datasets: ?cursor=xxx&limit=50. "
                "Cursors are stable across data changes unlike offset pagination."
            ),
            tags=["api", "pagination", "performance"],
        )

        api_idempotency = await graph.add_node(
            name="Idempotency Keys for Safe Retries",
            type="api_design",
            namespace="knowledge",
            description=(
                "Accept Idempotency-Key header for POST/PUT/DELETE. "
                "Store key+response for 24h. Return cached response if key seen again. "
                "Critical for payment APIs."
            ),
            tags=["api", "reliability", "design"],
        )

        # Testing nodes
        test_pyramid = await graph.add_node(
            name="Testing Pyramid Strategy",
            type="testing",
            namespace="knowledge",
            description=(
                "70% unit tests (fast, isolated), 20% integration tests (API/DB), "
                "10% e2e tests (UI flows). Balance speed vs confidence."
            ),
            tags=["testing", "quality", "strategy"],
        )

        test_contract = await graph.add_node(
            name="API Contract Testing",
            type="testing",
            namespace="knowledge",
            description=(
                "Use OpenAPI/Swagger for contract definition. "
                "Validate requests/responses against schema. "
                "Use Pact for consumer-driven contract testing."
            ),
            tags=["testing", "api", "contracts"],
        )

        await graph.add_node(
            name="Test Data Builders",
            type="testing",
            namespace="knowledge",
            description=(
                "Use builder pattern for test data creation. "
                "Factory libraries: factory_boy (Python), factory-bot (Ruby), "
                "faker for realistic data."
            ),
            tags=["testing", "patterns", "data"],
        )

        # Deployment nodes
        deploy_blue_green = await graph.add_node(
            name="Blue-Green Deployment",
            type="deployment",
            namespace="knowledge",
            description=(
                "Run two identical production environments. "
                "Route traffic to blue, deploy to green, test, then switch. "
                "Instant rollback by switching back."
            ),
            tags=["deployment", "devops", "reliability"],
        )

        deploy_canary = await graph.add_node(
            name="Canary Deployment Pattern",
            type="deployment",
            namespace="knowledge",
            description=(
                "Gradually roll out to subset of users (5% → 25% → 50% → 100%). "
                "Monitor metrics at each stage. Automatic rollback on error threshold."
            ),
            tags=["deployment", "devops", "monitoring"],
        )

        progress.update(task, description="[green]✓[/green] Created 20 nodes")

        # Create edges
        task = progress.add_task("Connecting knowledge graph...", total=None)

        await graph.connect(auth_jwt.id, db_redis.id, "uses", weight=0.9)
        await graph.connect(auth_oauth.id, auth_jwt.id, "generates", weight=0.85)
        await graph.connect(auth_rbac.id, auth_jwt.id, "validates", weight=0.8)
        await graph.connect(auth_rate.id, db_redis.id, "uses", weight=0.9)
        await graph.connect(db_postgres.id, db_redis.id, "cached_by", weight=0.85)
        await graph.connect(db_pool.id, db_postgres.id, "optimizes", weight=0.8)
        await graph.connect(db_query.id, db_postgres.id, "optimizes", weight=0.9)
        await graph.connect(db_partition.id, db_postgres.id, "scales", weight=0.85)
        await graph.connect(api_rest.id, db_postgres.id, "queries", weight=0.75)
        await graph.connect(api_pagination.id, db_query.id, "prevents", weight=0.8)
        await graph.connect(api_idempotency.id, db_redis.id, "uses", weight=0.85)
        await graph.connect(test_contract.id, api_rest.id, "validates", weight=0.9)
        await graph.connect(test_pyramid.id, test_contract.id, "includes", weight=0.7)
        await graph.connect(deploy_blue_green.id, db_migration.id, "requires", weight=0.85)
        await graph.connect(deploy_canary.id, deploy_blue_green.id, "alternative_to", weight=0.6)

        progress.update(task, description="[green]✓[/green] Created 15 edges")

        # Create experiences
        task = progress.add_task("Saving experiences...", total=None)

        await experience.save(
            content=(
                "Token bucket rate limiting solved API abuse issue. "
                "Implemented in 4 hours using Redis. Reduced malicious traffic by 95%."
            ),
            type="solution",
            context="Security incident response",
            confidence="high",
            tags=["rate-limiting", "security", "redis"],
        )

        await experience.save(
            content=(
                "Repository pattern with Unit of Work keeps business logic clean and testable. "
                "Learned from Domain-Driven Design book."
            ),
            type="pattern",
            context="Code architecture refactoring",
            confidence="high",
            tags=["architecture", "patterns", "ddd"],
        )

        await experience.save(
            content=(
                "Switching from offset to cursor pagination improved API performance by 10x "
                "for large result sets. Users noticed faster scrolling."
            ),
            type="solution",
            context="Performance optimization sprint",
            confidence="high",
            tags=["pagination", "performance", "api"],
        )

        await experience.save(
            content=(
                "Blue-green deployment reduced downtime from 5 minutes to <1 second. "
                "Infrastructure cost increased by 20% but worth it for uptime."
            ),
            type="solution",
            context="Infrastructure improvement project",
            confidence="high",
            tags=["deployment", "devops", "reliability"],
        )

        await experience.save(
            content=(
                "PostgreSQL JSONB indexes are tricky. "
                "GIN index helped but expression indexes on specific keys gave 100x speedup."
            ),
            type="gotcha",
            context="Database performance investigation",
            confidence="high",
            tags=["postgresql", "indexing", "performance"],
        )

        await experience.save(
            content=(
                "Decided against GraphQL migration. "
                "Team expertise is in REST, and migration cost outweighs benefits for our use case."
            ),
            type="decision",
            context="API architecture discussion",
            confidence="high",
            tags=["graphql", "rest", "architecture"],
        )

        await experience.save(
            content=(
                "Using Argon2id instead of bcrypt for new passwords. "
                "Existing bcrypt hashes will be upgraded on next login."
            ),
            type="decision",
            context="Security audit findings",
            confidence="medium",
            tags=["security", "cryptography", "passwords"],
        )

        await experience.save(
            content=(
                "Idempotency keys saved us during payment processing outage. "
                "Users retried requests but weren't charged twice."
            ),
            type="solution",
            context="Production incident review",
            confidence="high",
            tags=["idempotency", "payments", "reliability"],
        )

        await experience.save(
            content=(
                "Test pyramid ratio was inverted (too many e2e tests). "
                "Refactored to more unit tests. Test suite now runs in 2 min instead of 20."
            ),
            type="gotcha",
            context="Testing infrastructure improvement",
            confidence="high",
            tags=["testing", "performance", "quality"],
        )

        await experience.save(
            content=(
                "OAuth2 state parameter MUST be random and validated. "
                "Prevented CSRF attack during security audit."
            ),
            type="gotcha",
            context="Security code review",
            confidence="high",
            tags=["oauth2", "security", "csrf"],
        )

        progress.update(task, description="[green]✓[/green] Saved 10 experiences")

        # Create projects
        task = progress.add_task("Creating projects...", total=None)

        project1 = await memory.create_project(
            name="E-Commerce API v2",
            goals=[
                "Migrate to microservices architecture",
                "Implement GraphQL gateway",
                "Reduce p95 latency to <100ms",
            ],
            stakeholders=["Backend Team", "Product", "DevOps"],
            success_metrics=["<100ms p95 latency", ">99.9% uptime", "10M requests/day"],
        )

        await memory.log_progress(
            project_id=project1.id,
            action="Implemented JWT authentication",
            result="Auth service deployed, tests passing",
            next_step="Add OAuth2 social login",
        )

        await memory.log_progress(
            project_id=project1.id,
            action="Added rate limiting middleware",
            result="Token bucket algorithm active on all endpoints",
            next_step="Optimize database queries with Redis caching",
        )

        await memory.update_project(project1.id, phase="active", active=True)

        project2 = await memory.create_project(
            name="Mobile App Backend",
            goals=[
                "Build REST API for mobile clients",
                "Support offline-first sync",
                "Handle 1M concurrent users",
            ],
            stakeholders=["Mobile Team", "Backend Team"],
            success_metrics=["<200ms API response time", "99.95% uptime"],
        )

        await memory.log_progress(
            project_id=project2.id,
            action="Designed API contract using OpenAPI",
            result="Contract reviewed and approved by mobile team",
            next_step="Implement core endpoints",
        )

        await memory.update_project(project2.id, phase="active", active=True)

        project3 = await memory.create_project(
            name="Database Migration to PostgreSQL 16",
            goals=[
                "Zero downtime migration",
                "Improve query performance by 30%",
                "Enable logical replication",
            ],
            stakeholders=["Database Team", "DevOps"],
            success_metrics=["Zero downtime", "30% faster queries", "Replication lag <1s"],
        )

        await memory.log_progress(
            project_id=project3.id,
            action="Completed performance testing on staging",
            result="All queries 35% faster, replication working",
            next_step="Schedule production migration",
        )

        await memory.update_project(project3.id, phase="paused", active=False)

        progress.update(task, description="[green]✓[/green] Created 3 projects")

        # Create ideas
        task = progress.add_task("Creating ideas...", total=None)

        idea1 = await ideas.create(
            title="Implement GraphQL federation for microservices",
            category="architecture",
            score=8.5,
            properties={
                "estimated_effort": "3 sprints",
                "impact": "high",
                "complexity": "high",
            },
        )
        await ideas.advance(idea1.id)

        idea2 = await ideas.create(
            title="Add real-time notifications using WebSockets",
            category="feature",
            score=7.0,
            properties={
                "estimated_effort": "2 sprints",
                "impact": "medium",
                "complexity": "medium",
            },
        )
        await ideas.advance(idea2.id)
        await ideas.advance(idea2.id)

        await ideas.create(
            title="Migrate logging to OpenTelemetry",
            category="infrastructure",
            score=6.5,
            properties={
                "estimated_effort": "1 sprint",
                "impact": "medium",
                "complexity": "low",
            },
        )

        idea4 = await ideas.create(
            title="Implement event sourcing for order service",
            category="architecture",
            score=9.0,
            properties={
                "estimated_effort": "4 sprints",
                "impact": "high",
                "complexity": "very high",
            },
        )
        await ideas.advance(idea4.id)
        await ideas.advance(idea4.id)
        await ideas.advance(idea4.id)

        await ideas.create(
            title="Add API usage analytics dashboard",
            category="monitoring",
            score=5.5,
            properties={
                "estimated_effort": "1 sprint",
                "impact": "low",
                "complexity": "low",
            },
        )

        progress.update(task, description="[green]✓[/green] Created 5 ideas")

    # Show summary
    stats = await graph.stats()

    await store.close()

    console.print("\n[bold green]✓ Sample workspace created successfully![/bold green]\n")
    console.print(f"[cyan]Location:[/cyan] {db_path}")
    console.print(f"[cyan]Nodes:[/cyan] {stats['total_nodes']}")
    console.print(f"[cyan]Edges:[/cyan] {stats['total_edges']}")
    console.print("[cyan]Projects:[/cyan] 3 (1 active, 1 paused, 1 planning)")
    console.print("[cyan]Ideas:[/cyan] 5 (various statuses)")
    console.print("[cyan]Experiences:[/cyan] 10 (high confidence solutions and patterns)\n")

    console.print("[dim]To explore this workspace, start the engram server:[/dim]")
    console.print(f"[dim]  cd {workspace_dir}[/dim]")
    console.print("[dim]  engram serve[/dim]\n")


if __name__ == "__main__":
    asyncio.run(create_sample_workspace())
