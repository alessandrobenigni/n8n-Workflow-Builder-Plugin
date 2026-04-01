# n8n Workflow Builder

A Claude Code plugin that turns plain English into deployed n8n workflows. Describe what you want to automate and the plugin handles node discovery, workflow design, code generation, validation, and deployment — all through conversation.

## What It Does

- **`/n8n`** — Create, update, and iterate on workflows conversationally
- **`/n8n-manage`** — List, inspect, activate, deactivate, archive, and execute workflows
- **`/n8n-browse`** — Explore available nodes, patterns, and workflow techniques

## Examples

```
/n8n send me a Slack message every morning at 9am with the weather forecast
/n8n when a new row is added to Google Sheets, enrich the email with Clearbit and add to HubSpot
/n8n build a RAG chatbot that ingests PDFs, stores them in a vector database, and answers questions
/n8n-manage list my active workflows
/n8n-browse what AI agent nodes are available?
```

## Prerequisites

### 1. n8n-mcp server

You need an n8n-mcp server connected to your Claude Code environment. Follow the setup at [github.com/czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp).

### 2. Configure MCP in Claude Code

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "url": "http://localhost:3001/mcp",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

### 3. Install plugin

```bash
claude plugin add https://github.com/TheSauceSuite/n8n-plugin
```

## How It Works

### Hybrid Architecture

The plugin uses **two complementary systems**:

**Local SQLite database** (ships with plugin, 75MB):
- 1,396 nodes with full property schemas (22.3 MB of parameter definitions)
- Pre-computed intent tags for zero-token, 100% recall searches
- FTS5 full-text search with BM25 ranking
- 2,737 workflow templates with complete JSON
- 215 real-world node configurations from popular templates

**n8n-mcp server** (requires running n8n instance):
- SDK reference (patterns, expressions, coding guidelines)
- Curated node recommendations by workflow technique
- Workflow validation and auto-fix
- Workflow creation, update, execution, publishing
- Project and folder management

**Why hybrid?** Node discovery via the local DB is instant, unlimited, and burns zero tokens. The MCP handles everything that touches the live n8n instance (validation, deployment, execution).

### 8-Phase Flow

1. **Understand** — Parse intent, classify pattern, confirm understanding
2. **Discover** — Search local DB for nodes, get property schemas, find real-world examples
3. **Design** — Present visual blueprint for approval
4. **Refine** — Iteratively modify the design through conversation
5. **Build** — Generate SDK code with exact parameter names from local DB
6. **Validate** — Auto-validate and fix (3-tier escalation: auto → agent → user)
7. **Deploy** — Create workflow in n8n, optionally activate
8. **Iterate** — "Now add X", "change Y" — loops back without starting over

For complex workflows (9+ nodes), parallel research agents discover nodes simultaneously across functional domains.

## Supported Patterns

| Pattern | Example |
|---------|---------|
| Linear chain | Schedule → Fetch → Send |
| Branching (If/Switch) | Webhook → Check Priority → Route |
| Parallel execution | Trigger → [A + B] → Merge → Process |
| Batch processing | Fetch All → Loop → Process Each → Done |
| AI Agent | Chat → Agent (LLM + Tools + Memory) → Response |
| RAG pipeline | Ingest docs → Embed → Store + Chat → Retrieve → Answer |
| Multi-trigger | [Webhook + Schedule] → Shared Chain |
| Error handling | Node → Success / Error Handler |
| Sub-workflow | Main → Execute Sub-workflow → Continue |
| Form-based | Form Trigger → Pages → Process → Respond |

## Architecture

```
.claude-plugin/
  plugin.json                    Plugin metadata

data/
  nodes.db                       SQLite: 1,396 nodes with tags, schemas, templates
  search.py                      Search utility (tag-based + FTS5 + operations)
  generate_tags.py               Tag generation script (run to rebuild tags)
  tag_taxonomy.md                Tag taxonomy documentation

skills/
  n8n/SKILL.md                   Main skill — 8-phase workflow builder
  n8n/references/                Pattern, blueprint, and orchestration guides
  n8n-manage/SKILL.md            Lifecycle management
  n8n-browse/SKILL.md            Node and pattern exploration

agents/
  n8n-node-researcher.md         Parallel node discovery via local DB (Sonnet)
  n8n-code-writer.md             SDK code generation (Opus)
  n8n-validator.md               Validation fix loop (Sonnet)
```

### Tag-Based Search

Every node has pre-computed semantic tags (avg 5.1 per node). Search by intent returns ALL relevant nodes in one query:

| User Intent | Tag | Example Matches |
|-------------|-----|-----------------|
| "send notification" | `notification` | Slack, Gmail, Telegram, Discord, Teams, Twilio, PagerDuty, 40+ more |
| "store in database" | `database` | Postgres, MySQL, MongoDB, Redis, DataTable, BigQuery, 25+ |
| "build a chatbot" | `chatbot` | Chat Trigger, AI Agent, Memory, OpenAI Assistant |
| "RAG pipeline" | `rag` | All vector stores, embeddings, retrievers, doc loaders, splitters |

## License

MIT
