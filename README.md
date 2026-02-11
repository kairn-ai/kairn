# Kairn

> Context-aware knowledge engine for AI assistants.

Other tools give your AI a memory. **Kairn** gives it a knowledge graph with intelligent context routing. It knows what to load, when to load it, and how much — so your AI stays focused, not overwhelmed.

```bash
pip install kairn-ai
kairn init ~/brain
kairn serve ~/brain
```

## Why Kairn?

Every AI conversation starts from scratch. Previous insights, decisions, and patterns — gone. Existing memory tools store flat key-value pairs that can't represent relationships or surface the *right* context at the *right* time.

Kairn is different:

- **Context Router + Progressive Disclosure** — Automatically loads relevant subgraphs based on keywords, starting with summaries and drilling into details only when needed. No other tool does this.
- **Knowledge Graph with FTS5** — Not flat storage. Typed relationships (`depends-on`, `resolves`, `causes`) between nodes with full-text search across everything.
- **Experience Decay + Auto-Promotion** — Experiences lose relevance over time (biological decay model). Frequently-accessed experiences auto-promote to permanent knowledge. Your AI naturally forgets what doesn't matter.
- **5 MCP Tools** — Consolidated, domain-grouped tools that keep context windows lean. Works with Claude Desktop, Cursor, VS Code, Windsurf, and any MCP client.
- **Team Workspaces with RBAC** — Per-workspace isolation with JWT auth and role-based access control.

## Quick Start

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kairn": {
      "command": "kairn",
      "args": ["serve", "~/brain"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp-servers.json`:

```json
{
  "mcpServers": {
    "kairn": {
      "command": "kairn",
      "args": ["serve", "~/brain"],
      "env": {
        "KAIRN_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

Restart your editor. Kairn's 5 tools appear in the MCP section.

## 5 Tools (kn_ prefix)

All tools follow MCP protocol with JSON responses. Each tool uses an `action` parameter to select the operation.

### `kn_graph` — Knowledge Graph

Direct operations on the knowledge graph: create, connect, search, and remove nodes and edges.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `add` | Create a node | name, type |
| `connect` | Create a weighted edge | source_id, target_id, edge_type |
| `query` | Search by text, type, tags, namespace | *(all optional)* |
| `remove` | Soft-delete node or edge (reversible) | node_id *or* source_id + target_id + edge_type |
| `status` | Graph stats and health | *(none)* |

### `kn_project` — Project Memory

Manage projects and log session activity.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `create` | New project (starts in "planning") | name |
| `update` | Modify existing project | project_id, name |
| `list` | List projects, switch active | *(optional: active_only, set_active)* |
| `log` | Record progress or failure entry | project_id, action_text |

### `kn_experience` — Experience Memory

Store and retrieve experiential memories with time-based decay.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `save` | Store an experience | content, type |
| `search` | Find past experiences by relevance | *(all optional)* |
| `prune` | Remove decayed experiences | *(optional: threshold)* |

### `kn_idea` — Idea Tracking

Capture and track ideas through a lifecycle: draft → evaluating → approved → implementing → done → archived.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `create` | New idea (starts as "draft") | title |
| `update` | Modify existing idea | idea_id, title |
| `list` | List and filter ideas | *(optional: status, category)* |

### `kn_intel` — Intelligence Layer *(default entry point)*

The primary interface for storing and retrieving knowledge. Routes automatically by confidence and type. **Use this as the default** — drop to lower-level tools only when you need direct control.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `learn` | Store knowledge (high confidence → permanent node + experience; medium/low → decaying experience only) | content, type |
| `recall` | Surface relevant past knowledge | *(optional: topic)* |
| `crossref` | Find similar solutions across workspaces | problem |
| `context` | Keywords → relevant subgraph | keywords |
| `related` | Graph traversal from a node | node_id |

## Resources & Prompts

**Resources** (read-only context for MCP clients):
- `kn://status` — Graph overview, active project
- `kn://projects` — All projects with recent progress
- `kn://memories` — Recent high-relevance experiences

**Prompts** (session management):
- `kn_bootup` — Load active project, recent progress, and top memories (session start)
- `kn_review` — Summarize session and suggest next steps (session end)

## How It Works

### Architecture

```
Any MCP Client (Claude, Cursor, VS Code)
        │
        ▼ MCP Protocol (stdio)
FastMCP Server (5 tools)
        │
   ┌────┼────┐
   ▼    ▼    ▼
Graph  Memory  Intelligence
Engine Engine  Layer
   │    │      │
   └────┼──────┘
        ▼
   SQLite + FTS5
   (per-workspace)
```

### Decay Model

Experiences decrease in relevance exponentially:

```
relevance(t) = initial_score × e^(-decay_rate × days)
```

| Type | Half-life | Notes |
|------|-----------|-------|
| solution | 200 days | Stable, durable |
| pattern | 300 days | Architectural knowledge |
| decision | 100 days | Context-dependent |
| workaround | 50 days | Temporary fixes fade fast |
| gotcha | 200 days | Tricky pitfalls stay relevant |

**Confidence routing** via `kn_intel(action="learn")`:
- `high` → Permanent node + experience (no decay)
- `medium` → Experience with 2× decay
- `low` → Experience with 4× decay
- Auto-promotion: 5+ accesses → permanent node

## CLI

```bash
kairn init <path>              # Initialize workspace
kairn serve <path>             # Start MCP server (stdio)
kairn status <path>            # Graph stats
kairn demo <path>              # Interactive tutorial
kairn benchmark <path>         # Performance benchmarks
kairn token-audit <path>       # Audit tool token usage
```

## Configuration

```bash
KAIRN_LOG_LEVEL=INFO|DEBUG|WARNING    # Default: WARNING
KAIRN_DB_PATH=~/brain/.kairn         # Default: {workspace}/.kairn
KAIRN_CACHE_SIZE=100                  # LRU cache entries
KAIRN_JWT_SECRET=<your-secret>        # Required for team features
```

## Development

```bash
git clone https://github.com/kairn-ai/kairn
cd kairn
pip install -e ".[dev,team]"
pytest tests/ -v --cov
ruff check src/ && ruff format src/
```

### Project Structure

```
src/kairn/
├── server.py              # FastMCP server + 5 consolidated tools
├── cli.py                 # CLI commands
├── config.py              # Configuration
├── core/
│   ├── graph.py           # GraphEngine
│   ├── memory.py          # ProjectMemory
│   ├── experience.py      # ExperienceEngine
│   ├── ideas.py           # IdeaEngine
│   ├── intelligence.py    # IntelligenceLayer
│   └── router.py          # ContextRouter
├── storage/
│   ├── base.py            # Storage interface
│   └── sqlite_store.py    # SQLite + FTS5 implementation
├── models/                # Data models
├── events/                # Event bus
└── auth/                  # JWT + RBAC (team feature)
```

## Performance

Typical operation times on modern hardware:

| Operation | Time |
|-----------|------|
| `kn_graph(action="add")` | 2-5ms |
| `kn_graph(action="query")` (100 nodes) | 5-15ms |
| `kn_graph(action="connect")` | 1-3ms |
| `kn_intel(action="recall")` (graph traversal) | 10-50ms |
| `kn_intel(action="crossref")` (cross-workspace) | 20-100ms |

## License

MIT
