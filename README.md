# engram

> Your AI's engram — memory that persists, decays, and connects.

**engram** is a graph-native knowledge engine that gives any AI assistant persistent memory with natural decay, knowledge relationships, and team collaboration. Think of it as a second brain that remembers what matters, forgets what doesn't, and connects the dots automatically.

## Why engram?

- **AI forgets everything**: Each conversation starts from scratch. Critical context from previous sessions is lost. Patterns learned are never reused.
- **Manual memory is pain**: Keeping notes, maintaining knowledge bases, and organizing information manually doesn't scale.
- **Flat key-value stores don't work**: Simple storage like Redis or JSON files can't represent relationships, decay importance naturally, or surface context when needed.
- **Team memory is missing**: Sharing knowledge across workspaces requires manual sync. Multi-user systems have no built-in collaboration model.

engram solves all of this with a graph-native approach and configurable memory decay.

## Features

### Memory that learns and forgets

- **Natural decay**: Experiences lose relevance over time with configurable half-lives (solution: 200 days, pattern: 300 days, gotcha: 200 days)
- **Persistent knowledge**: High-confidence information stays permanent
- **Auto-promotion**: Frequently-accessed experiences automatically graduate to permanent knowledge nodes
- **Confidence routing**: High confidence → permanent node; medium/low → decaying experience

### Knowledge graph with semantic routing

- **Full-text search**: FTS5-powered search across all knowledge, notes, and experiences
- **Progressive disclosure**: Start with summaries, drill into details, read full content
- **Namespace isolation**: Separate `knowledge`, `ideas`, `projects`, and `experiences` namespaces
- **Typed relationships**: Create semantic edges like `causes`, `relates-to`, `resolves`, `depends-on`

### Intelligence layer

- `eg_learn` — Store knowledge with confidence-based routing (node or experience)
- `eg_recall` — Surface relevant past context for the current topic
- `eg_crossref` — Find similar solutions across workspaces
- `eg_context` — Keywords → relevant subgraph with progressive disclosure
- `eg_related` — Graph traversal (BFS/DFS) to find connected ideas

### Session continuity

- **Auto-save/resume**: Sessions persist across restarts with full context recovery
- **Project tracking**: Log progress milestones and failures with outcomes
- **Idea lifecycle**: Draft → evaluating → approved → implementing → done
- **Session summaries**: Automatic review prompts at session end

### Team ready

- **Per-workspace SQLite**: Each team member gets isolated data + shared collaboration
- **JWT authentication**: Secure token-based access with expiry
- **RBAC permissions**: Role-based control (viewer, editor, admin per workspace)
- **Knowledge sharing**: Share nodes with visibility controls

## Quick Start

### Installation

```bash
pip install engram-ai
```

### Initialize workspace

```bash
engram init ~/my-brain
```

This creates a local SQLite database at `~/my-brain/.engram/db.sqlite`.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["serve", "~/my-brain"]
    }
  }
}
```

Restart Claude Desktop. The engram tools will appear in the MCP section.

### Cursor

Add to `.cursor/mcp-servers.json` (or equivalent in your Cursor config):

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["serve", "~/my-brain"],
      "env": {
        "ENGRAM_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

See `examples/claude-desktop.json` and `examples/cursor-config.json` for complete configs.

## 18 Tools (eg_ prefix)

All tools follow MCP protocol with JSON responses. Responses include `_v: "1.0"` for versioning.

### Graph (5)

| Tool | Description | Example |
|------|-------------|---------|
| `eg_add` | Add node to knowledge graph | `eg_add("React Hooks", "pattern", "knowledge")` |
| `eg_connect` | Create typed edge between nodes | `eg_connect(id1, id2, "depends-on", weight=0.8)` |
| `eg_query` | Search by text, type, tags, namespace | `eg_query(text="database", namespace="knowledge")` |
| `eg_remove` | Soft-delete node or edge (undo-safe) | `eg_remove(node_id=id)` |
| `eg_status` | Graph stats, health, system overview | Returns: node count, edge count, namespaces |

### Project Memory (3)

| Tool | Description | Example |
|------|-------------|---------|
| `eg_project` | Create or update project | `eg_project("Auth Refactor", goals=[...])` |
| `eg_projects` | List projects, switch active | `eg_projects(active_only=True, set_active=id)` |
| `eg_log` | Log progress or failure entry | `eg_log(project_id, "Implemented OAuth", type="progress")` |

### Experience Memory (3)

| Tool | Description | Example |
|------|-------------|---------|
| `eg_save` | Save experience with decay | `eg_save("Never use X in Y", type="gotcha", confidence="high")` |
| `eg_memories` | Decay-aware experience search | `eg_memories(text="database", min_relevance=0.1)` |
| `eg_prune` | Remove expired experiences (archive first) | `eg_prune(threshold=0.01)` |

### Ideas (2)

| Tool | Description | Example |
|------|-------------|---------|
| `eg_idea` | Create or update idea | `eg_idea("Streaming API", status="implementing")` |
| `eg_ideas` | List/filter ideas by status, category | `eg_ideas(status="approved")` |

### Intelligence (5)

| Tool | Description | Example |
|------|-------------|---------|
| `eg_learn` | Store knowledge (confidence routing) | `eg_learn("Use immutable patterns", type="decision", confidence="high")` |
| `eg_recall` | Surface relevant past knowledge | `eg_recall(topic="performance", limit=5)` |
| `eg_crossref` | Find similar solutions across workspaces | `eg_crossref(problem="N+1 queries")` |
| `eg_context` | Keywords → relevant subgraph | `eg_context("database caching")` |
| `eg_related` | Graph traversal (BFS/DFS) | `eg_related(node_id, depth=2)` |

## Resources (3)

These are read-only context providers for MCP clients:

- `eg://status` — Graph and system overview, active project
- `eg://projects` — All projects with recent progress summaries
- `eg://memories` — Recent high-relevance experiences (>0.1 relevance)

## Prompts (2)

These are context generators for session management:

- `eg_bootup` — Load active project, recent progress, and top memories (use at session start)
- `eg_review` — Summarize what happened and suggest next steps (use at session end)

## How it works

### Architecture

```
Any MCP Client (Claude, Cursor, VS Code)
        │
        ▼ MCP Protocol (stdio)
FastMCP Server (18 tools)
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

### Storage

**SQLite + FTS5** backend provides:
- ACID transactions for consistency
- Full-text search across all content
- Efficient indexing for graph queries
- Per-workspace isolation

### Decay Model

Relevance of experiences decreases exponentially:

```
relevance(t) = initial_score × e^(-decay_rate × days)
```

Half-life values (configurable in code):
- **solution**: 200 days (stable, durable)
- **pattern**: 300 days (architectural knowledge)
- **decision**: 100 days (context-dependent)
- **workaround**: 50 days (temporary fixes fade fast)
- **gotcha**: 200 days (tricky pitfalls stay relevant)

Confidence affects decay:
- `high` → Creates permanent node (no decay) + experience
- `medium` → Experience only (2× base decay rate)
- `low` → Experience only (4× base decay rate)

### Confidence Routing

When using `eg_learn`:

1. **high confidence**: Creates permanent node in knowledge graph + linked experience
2. **medium confidence**: Creates experience with 2× decay multiplier
3. **low confidence**: Creates experience with 4× decay multiplier
4. **auto-promotion**: Experiences accessed 5+ times auto-promote to permanent nodes

## CLI

```bash
# Workspace management
engram init <path>              # Initialize new workspace
engram serve <path>             # Start MCP server (stdout)
engram status <path>            # Show workspace graph stats
engram demo <path>              # Interactive tutorial

# Utilities
engram benchmark <path>         # Performance benchmarks
engram token-audit <path>       # Audit tool token usage
engram workspace create         # Create team workspace (team feature)
engram workspace join           # Join existing workspace (team feature)
engram workspace leave          # Leave workspace (team feature)
```

## Development

### Setup

```bash
git clone https://github.com/engram-ai/engram
cd engram
pip install -e ".[dev,team]"
```

### Run tests

```bash
pytest tests/ -v                # Run all tests
pytest tests/ -v --cov          # With coverage
pytest tests/test_server.py -v  # Single file
```

### Code quality

```bash
ruff check src/                 # Lint
ruff format src/                # Format
pyright src/                    # Type check
```

### Architecture

```
src/engram/
├── server.py                   # FastMCP server + 18 tools
├── cli.py                      # CLI commands
├── config.py                   # Configuration
├── core/
│   ├── graph.py               # GraphEngine (5 tools)
│   ├── memory.py              # ProjectMemory (3 tools)
│   ├── experience.py          # ExperienceEngine (3 tools)
│   ├── ideas.py               # IdeaEngine (2 tools)
│   ├── intelligence.py        # IntelligenceLayer (5 tools)
│   └── router.py              # ContextRouter (search routing)
├── storage/
│   ├── base.py                # Storage interface
│   └── sqlite_store.py        # SQLite implementation
├── events/
│   └── bus.py                 # Event bus for system integration
└── auth/                       # JWT + RBAC (team feature)
```

## Configuration

### Environment variables

```bash
ENGRAM_LOG_LEVEL=INFO|DEBUG|WARNING    # Default: WARNING
ENGRAM_DB_PATH=~/my-brain/.engram      # Default: {workspace}/.engram
ENGRAM_CACHE_SIZE=100                  # LRU cache entries
```

## Performance

Typical operation times on modern hardware:

- `eg_add`: 2-5ms
- `eg_query` (100 nodes): 5-15ms
- `eg_connect`: 1-3ms
- `eg_recall` (graph traversal): 10-50ms
- `eg_crossref` (cross-workspace): 20-100ms

See `examples/benchmark.py` for detailed benchmarks.

## License

MIT
