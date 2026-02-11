# Kairn MCP Tool Consolidation Plan

## Overview

Consolidate 18 individual MCP tools into 5 domain-grouped tools, each using an `action` parameter to dispatch internally. Resources (3) and prompts (2) remain unchanged.

**Result: 18 tools → 5 tools**

---

## Current Tool Inventory

| # | Current Tool | Domain | Purpose |
|---|---|---|---|
| 1 | `kn_add` | Graph | Add node |
| 2 | `kn_connect` | Graph | Create edge |
| 3 | `kn_query` | Graph | Search nodes |
| 4 | `kn_remove` | Graph | Remove node or edge |
| 5 | `kn_status` | Graph | System stats |
| 6 | `kn_project` | Project | Create/update project |
| 7 | `kn_projects` | Project | List projects / set active |
| 8 | `kn_log` | Project | Log progress/failure |
| 9 | `kn_save` | Experience | Save experience |
| 10 | `kn_memories` | Experience | Search experiences |
| 11 | `kn_prune` | Experience | Remove expired experiences |
| 12 | `kn_idea` | Idea | Create/update idea |
| 13 | `kn_ideas` | Idea | List/filter ideas |
| 14 | `kn_learn` | Intelligence | Store knowledge |
| 15 | `kn_recall` | Intelligence | Surface past knowledge |
| 16 | `kn_crossref` | Intelligence | Cross-workspace search |
| 17 | `kn_context` | Intelligence | Keyword to subgraph |
| 18 | `kn_related` | Intelligence | Graph traversal |

---

## Consolidated Tool Definitions

### 1. `kn_graph`

**Replaces:** `kn_add`, `kn_connect`, `kn_query`, `kn_remove`, `kn_status`

**Tool description:**
> Direct operations on the knowledge graph: create, connect, search, and remove nodes and edges. Use this for structured knowledge that should persist permanently regardless of confidence level. For storing knowledge learned during a conversation, prefer kn_intel (action="learn") which automatically decides storage strategy.
>
> **Actions:**
> - **add** — Create a node. Requires: name, type. Optional: namespace, description, tags.
> - **connect** — Create a weighted, typed edge between two existing nodes. Requires: source_id, target_id, edge_type. Optional: weight.
> - **query** — Search nodes by text match, type, tags, or namespace. All filters optional. Returns matching nodes.
> - **remove** — Soft-delete a node (by node_id) or an edge (by source_id + target_id + edge_type). Reversible.
> - **status** — Return node/edge counts and system health. No additional parameters.

**Parameters:**

| Parameter | Type | Used By Actions | Description |
|---|---|---|---|
| `action` | str (required) | all | add \| connect \| query \| remove \| status |
| `name` | str | add | Node name |
| `type` | str | add | Node type (e.g. concept, pattern, tool, language) |
| `namespace` | str | add | Organizational namespace (default: "knowledge") |
| `description` | str \| None | add | Node description |
| `tags` | list[str] \| None | add, query | Tags for categorization or filtering |
| `source_id` | str | connect, remove | Source node ID for edge operations |
| `target_id` | str | connect, remove | Target node ID for edge operations |
| `edge_type` | str | connect, remove | Relationship type label for the edge |
| `weight` | float | connect | Edge weight 0.0–1.0 (default: 1.0) |
| `node_id` | str | remove | Node ID to remove |
| `text` | str \| None | query | Full-text search query |
| `node_type` | str \| None | query | Filter by node type |
| `detail` | str | query | "summary" or "full" (default: "summary") |
| `limit` | int | query | Max results 1–50 (default: 10) |
| `offset` | int | query | Pagination offset (default: 0) |

---

### 2. `kn_project`

**Replaces:** `kn_project`, `kn_projects`, `kn_log`

**Tool description:**
> Manage projects and log session activity. Projects track goals, phases, and progress over time. Use action="log" to record what was accomplished or what failed during a session — this builds the history that kn_bootup and kn_review use to maintain continuity across sessions.
>
> **Actions:**
> - **create** — Create a new project (starts in "planning" phase). Requires: name. Optional: goals, stakeholders, success_metrics.
> - **update** — Update an existing project's name, phase, or metadata. Requires: project_id, name. Optional: phase (planning|active|paused|done), goals, stakeholders, success_metrics.
> - **list** — List projects. Optional: active_only. Use set_active with a project ID to switch the active project.
> - **log** — Record a progress or failure entry against a project. Requires: project_id, action_text. Optional: type (progress|failure, default progress), result, next_step.

**Parameters:**

| Parameter | Type | Used By Actions | Description |
|---|---|---|---|
| `action` | str (required) | all | create \| update \| list \| log |
| `name` | str | create, update | Project name |
| `project_id` | str | update, log | Existing project ID |
| `phase` | str \| None | update | Phase: planning \| active \| paused \| done |
| `goals` | list[str] \| None | create, update | Project goals |
| `stakeholders` | list[str] \| None | create, update | Stakeholders |
| `success_metrics` | list[str] \| None | create, update | Success metrics / KPIs |
| `active_only` | bool | list | Only show active projects (default: false) |
| `set_active` | str \| None | list | Project ID to set as active |
| `action_text` | str | log | What was done or what failed |
| `type` | str | log | "progress" or "failure" (default: "progress") |
| `result` | str \| None | log | Outcome or error message |
| `next_step` | str \| None | log | Recommended next step |

---

### 3. `kn_experience`

**Replaces:** `kn_save`, `kn_memories`, `kn_prune`

**Tool description:**
> Store and retrieve experiential memories that decay over time. Unlike permanent graph nodes, experiences lose relevance based on their type and confidence — workarounds fade fastest, patterns persist longest. Use this for direct experience management. For the common case of saving something learned in conversation, prefer kn_intel (action="learn") which chooses the right storage automatically.
>
> **Actions:**
> - **save** — Store an experience. Requires: content, type (solution|pattern|decision|workaround|gotcha). Optional: context, confidence (high|medium|low — lower confidence decays faster), tags.
> - **search** — Find past experiences ranked by current relevance. Optional: text, type, min_relevance (0.0–1.0), limit, offset.
> - **prune** — Remove experiences that have decayed below a relevance threshold. Optional: threshold (default 0.01).

**Parameters:**

| Parameter | Type | Used By Actions | Description |
|---|---|---|---|
| `action` | str (required) | all | save \| search \| prune |
| `content` | str | save | What was learned or discovered |
| `type` | str | save, search | Experience type: solution \| pattern \| decision \| workaround \| gotcha |
| `context` | str \| None | save | Situation or circumstances when this was learned |
| `confidence` | str | save | high \| medium \| low — lower confidence decays faster (default: "high") |
| `tags` | list[str] \| None | save | Tags for categorization |
| `text` | str \| None | search | Full-text search query |
| `min_relevance` | float | search | Minimum relevance threshold 0.0–1.0 (default: 0.0) |
| `limit` | int | search | Max results 1–50 (default: 10) |
| `offset` | int | search | Pagination offset (default: 0) |
| `threshold` | float | prune | Remove experiences below this relevance (default: 0.01) |

---

### 4. `kn_idea`

**Replaces:** `kn_idea`, `kn_ideas`

**Tool description:**
> Capture and track ideas through a lifecycle: draft → evaluating → approved → implementing → done → archived. Ideas can be scored, categorized, and linked to knowledge graph nodes.
>
> **Actions:**
> - **create** — Create a new idea (starts as "draft"). Requires: title. Optional: category, score, link_to (node ID to create a graph edge to).
> - **update** — Update an existing idea's title, status, score, or category. Requires: idea_id, title. Optional: category, score, status, link_to.
> - **list** — List and filter ideas. Optional: status, category, limit, offset.

**Parameters:**

| Parameter | Type | Used By Actions | Description |
|---|---|---|---|
| `action` | str (required) | all | create \| update \| list |
| `title` | str | create, update | Idea title |
| `idea_id` | str | update | Existing idea ID |
| `category` | str \| None | create, update, list | Category classification |
| `score` | float \| None | create, update | Numerical score for prioritization |
| `status` | str \| None | update, list | Status: draft \| evaluating \| approved \| implementing \| done \| archived |
| `link_to` | str \| None | create, update | Node ID to link this idea to in the knowledge graph |
| `limit` | int | list | Max results 1–50 (default: 10) |
| `offset` | int | list | Pagination offset (default: 0) |

---

### 5. `kn_intel`

**Replaces:** `kn_learn`, `kn_recall`, `kn_crossref`, `kn_context`, `kn_related`

**Tool description:**
> The primary interface for storing and retrieving knowledge. Combines the knowledge graph, experience memory, and context routing to handle knowledge intelligently. Use this as the default when learning from or recalling knowledge in a conversation — it routes automatically based on confidence and type. Use the lower-level kn_graph, kn_experience, or kn_idea tools only when you need direct control over storage.
>
> **Actions:**
> - **learn** — Store knowledge from conversation. High confidence creates a permanent graph node AND an experience; medium/low confidence creates only a decaying experience. Requires: content, type (decision|pattern|solution|workaround|gotcha). Optional: context, confidence (high|medium|low, default high), tags.
> - **recall** — Retrieve relevant past knowledge combining graph nodes and experiences. Optional: topic, limit, min_relevance.
> - **crossref** — Search for similar solutions across other workspaces. Requires: problem. Optional: limit.
> - **context** — Find the relevant subgraph for a set of keywords. Returns a summary by default; use detail="full" for complete node data. Requires: keywords. Optional: detail, limit.
> - **related** — Traverse the graph outward from a node. Requires: node_id. Optional: depth (1–5, default 1), edge_type.

**Parameters:**

| Parameter | Type | Used By Actions | Description |
|---|---|---|---|
| `action` | str (required) | all | learn \| recall \| crossref \| context \| related |
| `content` | str | learn | What was learned, decided, or discovered |
| `type` | str | learn | Knowledge type: decision \| pattern \| solution \| workaround \| gotcha |
| `context` | str \| None | learn | Situation or circumstances when this was learned |
| `confidence` | str | learn | high = permanent node + experience, medium/low = decaying experience only (default: "high") |
| `tags` | list[str] \| None | learn | Tags for categorization |
| `topic` | str \| None | recall | Topic to recall knowledge about |
| `problem` | str | crossref | Problem description to find solutions for |
| `keywords` | str | context | Keywords to find relevant context for |
| `detail` | str | context | "summary" or "full" (default: "summary") |
| `node_id` | str | related | Starting node ID for graph traversal |
| `depth` | int | related | Traversal depth 1–5 (default: 1) |
| `edge_type` | str \| None | related | Filter traversal to a specific edge type |
| `limit` | int | recall, crossref, context, related | Max results 1–50 (default: 10) |
| `min_relevance` | float | recall | Minimum relevance threshold 0.0–1.0 (default: 0.0) |

---

## Unchanged Components

### Resources (3)
- `kn://status` — Graph and system overview
- `kn://projects` — All projects with progress summaries
- `kn://memories` — Recent high-relevance experiences

### Prompts (2)
- `kn_bootup` — Session start context
- `kn_review` — Session end review

---

## Description Design Principles

1. **Cross-tool routing guidance.** Each tool says when to use it vs. alternatives. The `kn_intel` ↔ `kn_graph`/`kn_experience` distinction is called out explicitly in every relevant description.

2. **Per-action parameter requirements.** Every action lists "Requires: X. Optional: Y." so the LLM knows exactly which params to fill for each action.

3. **Behavioral language, not implementation jargon.** "Experiences lose relevance over time" instead of "decay-aware FTS5 search." "Reversible" instead of "soft-delete with undo via restore."

4. **Session continuity motivation.** The `kn_project log` description explains *why* logging matters (bootup/review prompts consume it), motivating the LLM to actually use it.

5. **`kn_intel` positioned as the default.** Its description explicitly says "use this as the default" and names when to drop to lower-level tools. This is the most important routing decision the LLM makes.

---

## Research Findings: Industry Best Practices

The following is synthesized from web research on MCP tool design, LLM tool-use accuracy, and provider guidance (Anthropic, OpenAI, Google) as of early 2026.

### Tool Count and Selection Accuracy

Research consistently shows LLM tool selection accuracy degrades as the number of tools increases:

- **10–20 active tools** is the sweet spot across all providers (Google Gemini docs explicitly recommend this ceiling).
- **30–50 tools** is the practical upper limit before noticeable degradation without optimization.
- **Beyond ~100 tools**, severe issues emerge. The RAG-MCP paper showed retrieval-augmented filtering more than tripled accuracy (43% vs 14% baseline) at scale.
- Each tool's schema consumes tokens — 50 tools can eat 10,000–20,000 tokens of context before the user's query is even considered.

**Our consolidation (18 → 5) puts us well within the ideal range.**

### Compound Tools vs. Granular Tools

The industry consensus **strongly favors consolidation** for MCP servers:

- **Anthropic's engineering blog** provides explicit before/after examples: instead of `list_users` + `list_events` + `create_event`, implement `schedule_event` that handles all three internally. "Build a few thoughtful tools targeting specific high-impact workflows rather than wrapping every API endpoint."
- **Block's engineering playbook** documents their Linear MCP server evolving from 30+ granular tools down to consolidated tools, calling it "aggressive consolidation."
- **The STRAP pattern** (widely cited) reduced 96 tools to 10 domain tools using `resource` and `action` parameters, cutting context overhead by ~80% and reducing tool selection errors to near zero. Recommended specifically "when you have more than ~15 tools."
- **Compounding error math** (Huyench Chip): 95% accuracy per tool call = 60% accuracy over 10 calls. Fewer tool calls = fewer failure points.

### Tool Descriptions Are the Highest-Leverage Intervention

Every major provider treats descriptions as the #1 factor in tool performance:

- **Anthropic**: Claude achieved state-of-the-art SWE-bench performance "after we made precise refinements to tool descriptions" — not model changes, description changes. They recommend treating every text element (descriptions, error messages, parameter names) as instructions to the agent.
- **Best practices**: Use action-oriented verbs. State when NOT to use the tool. Describe boundaries with similar tools. Include output format expectations. Make error messages instructive ("User not found. Try searching by email." not a raw traceback).
- **Tool use examples**: Anthropic's beta feature for providing 1–5 input examples per tool improved complex parameter handling accuracy from 72% to 90%.

### Parameter Overload

LLMs struggle with too many optional parameters:

- **OpenAI**: Setups with < 20 arguments per tool are "in-distribution." Beyond that, reliability degrades.
- **Parameter hallucination**: LLMs sometimes invent plausible-sounding parameter values, especially with many optional params and ambiguous descriptions.
- **Mitigations**: Use enums/Literal types for constrained values. Provide sensible defaults. Flatten nested objects into top-level primitives. Keep parameter count minimal per action.

**Our consolidated tools max out at ~15 parameters each, but most actions only use 3–5. The "Used By Actions" column in our parameter tables is critical — it tells the LLM which params to ignore for a given action.**

### Naming Conventions

- **snake_case** is the de facto standard (90%+ of MCP servers). Our `kn_` prefix follows the recommended `{service}_{resource}` pattern.
- Names must match `^[a-zA-Z0-9_-]{1,64}$` per the MCP spec.
- Avoid hyphens (some platforms don't support them), abbreviations, and generic names.

### Key Sources

- [Anthropic: Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Anthropic: Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Block's Playbook for Designing MCP Servers](https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers)
- [Philipp Schmid: MCP is Not the Problem, It's your Server](https://www.philschmid.de/mcp-best-practices)
- [STRAP Pattern: 96 Tools to 10](https://almatuck.com/articles/reduced-mcp-tools-96-to-10-strap-pattern)
- [RAG-MCP Paper](https://arxiv.org/html/2505.03275v1)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [Google Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [MCP Specification: Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

---

## Migration Notes

- All tools continue to use the `_json()` helper and return `{"_v": "1.0", ...}` format.
- Error responses remain `{"_v": "1.0", "error": "message"}`.
- State initialization (`_init()`) and lazy locking are unchanged.
- Each consolidated tool validates the `action` parameter first and returns an error for unknown actions.
- Tests will need updating to call the new tool signatures.
