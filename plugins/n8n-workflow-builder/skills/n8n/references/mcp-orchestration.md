# Tool Orchestration Matrix

Single source of truth for how the plugin discovers nodes, builds code, validates, and deploys workflows. Every skill and agent MUST follow this document.

## Architecture

```
LOCAL DB (data/nodes.db)          MCP TOOLS (n8n-mcp server)
├── Node discovery (tags + FTS5)  ├── get_sdk_reference (SDK docs)
├── Node schemas (properties)     ├── get_suggested_nodes (curated recs)
├── Node operations & credentials ├── validate_workflow (code validation)
├── Template search               ├── create_workflow_from_code (deploy)
└── Real-world config examples    ├── update_workflow (modify)
                                  ├── execute_workflow (test)
SEARCH UTILITY (data/search.py)   ├── get_execution (results)
├── Tag-based intent search       ├── publish/unpublish_workflow
├── FTS5 text search              ├── archive_workflow
├── Node detail lookup            ├── search_workflows
├── Schema extraction             ├── get_workflow_details
├── Template config lookup        └── search_projects/folders
└── Format conversion (DB→SDK)

n8n REST API (requires N8N_API_KEY)
├── GET  /api/v1/credentials              List all credentials
├── POST /api/v1/credentials              Create a credential
├── GET  /api/v1/credentials/schema/{type} Get required fields for a credential type
├── DELETE /api/v1/credentials/{id}        Delete a credential
└── Auth: X-N8N-API-KEY header (NOT the MCP Bearer token)
├── Node operations & credentials ├── validate_workflow (code validation)
├── Template search               ├── create_workflow_from_code (deploy)
└── Real-world config examples    ├── update_workflow (modify)
                                  ├── execute_workflow (test)
SEARCH UTILITY (data/search.py)   ├── get_execution (results)
├── Tag-based intent search       ├── publish/unpublish_workflow
├── FTS5 text search              ├── archive_workflow
├── Node detail lookup            ├── search_workflows
├── Schema extraction             ├── get_workflow_details
├── Template config lookup        └── search_projects/folders
└── Format conversion (DB→SDK)

BROKEN (do NOT use):
├── get_node_types — "Invalid path - path traversal detected"
└── search_nodes — 5-result limit, fuzzy noise, high token cost
```

## Search Utility: data/search.py

The search utility is the PRIMARY interface to the local database. Use it instead of raw sqlite3 queries.

**Location:** `${CLAUDE_PLUGIN_ROOT}/data/search.py`

### Commands

```bash
# INTENT-BASED SEARCH (uses tags + FTS5 + operations + descriptions)
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "send notification" --no-tool-variants --core-only --limit 15

# DIRECT NAME SEARCH
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "gmail" --limit 10

# NODE DETAILS (accepts DB format or SDK format)
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --node nodes-base.slack

# PROPERTIES SCHEMA (filtered by resource/operation)
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --schema nodes-base.slack --resource message --operation post

# FULL SCHEMA (all properties)
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --schema nodes-base.slack

# REAL-WORLD CONFIG EXAMPLES from popular templates
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --template-configs nodes-base.slack

# SEARCH WORKFLOW TEMPLATES
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --template-search "lead enrichment"

# LIST ALL TRIGGERS
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --list-triggers

# LIST ALL AI/LANGCHAIN NODES
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --list-ai

# DATABASE STATS
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --stats

# JSON OUTPUT (for structured processing)
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "slack" --json
```

### Tag-Based Search

The database has a `tags` column on every node with pre-computed intent tags. Search.py uses these automatically, but you can also query directly:

**Available tags by category:**

| Intent | Tag | Finds |
|--------|-----|-------|
| Send messages/alerts | `messaging` | Slack, Discord, Telegram, Teams, WhatsApp, Gmail, 90+ more |
| Send email | `email` | Gmail, Outlook, SendGrid, Mailchimp, SES, SMTP, 30+ more |
| Notify someone | `notification` | All messaging + SMS + push services |
| Store in database | `database` | Postgres, MySQL, MongoDB, Redis, DataTable, BigQuery, 25+ |
| Store in spreadsheet | `spreadsheet` | Google Sheets, Excel, Airtable, Baserow, Notion |
| CRM operations | `crm` | HubSpot, Salesforce, Pipedrive, Zoho, 10+ |
| Project management | `project-management` | Jira, Linear, Trello, Asana, ClickUp, GitHub |
| AI/LLM models | `ai-llm` | All 15 LLM providers |
| AI agent | `ai-agent` | AI Agent, Agent Tool, OpenAI Assistant, Chat Trigger |
| AI chatbot | `chatbot` | Chat Trigger, Agent, all Memory nodes, Assistant |
| RAG pipeline | `rag` | All vector stores, embeddings, retrievers, doc loaders, splitters |
| Vector stores | `ai-vectorstore` | Pinecone, Qdrant, Chroma, Weaviate, Supabase, PGVector, 10+ |
| Embeddings | `ai-embedding` | All 9 embedding providers |
| AI memory | `ai-memory` | Buffer, Redis, Postgres, MongoDB, Zep, Motorhead, Xata |
| Triggers (time) | `trigger-on-schedule` | Schedule Trigger, Cron, Interval |
| Triggers (webhook) | `trigger-on-webhook` | Webhook, SSE Trigger, MCP Trigger |
| Triggers (form) | `trigger-on-form` | Form Trigger, Typeform, JotForm, Formstack, SurveyMonkey |
| Triggers (chat) | `trigger-on-chat` | Chat Trigger, Manual Chat Trigger |
| Triggers (event) | `trigger-on-event` | ALL 166 trigger nodes |
| Web scraping | `web-scraping` | HTTP Request, HTML Extract, Phantombuster, Airtop |
| File operations | `file-process` | Extract from File, Convert to File, Read PDF, Compression |
| File storage | `file-storage` | S3, Google Drive, Dropbox, OneDrive, FTP |
| Flow control | `flow-control` | If, Switch, Merge, Filter, Loop, Sort, Limit, Wait |
| Data transform | `data-transform` | Set, Aggregate, Summarize, Remove Duplicates, Compare |
| E-commerce | `ecommerce` | Stripe, Shopify, WooCommerce, PayPal |
| Support | `support` | Zendesk, Freshdesk, Intercom, Help Scout |
| Marketing | `marketing` | Mailchimp, ConvertKit, ActiveCampaign, Lemlist, Brevo |
| Developer tools | `developer` | GitHub, GitLab, Jenkins, SSH, NPM |

### Node ID Format Conversion

The database uses short format. The SDK requires full format:

| DB Format | SDK Format |
|-----------|-----------|
| `nodes-base.slack` | `n8n-nodes-base.slack` |
| `nodes-langchain.agent` | `@n8n/n8n-nodes-langchain.agent` |
| `n8n-nodes-community.X` | `n8n-nodes-community.X` (unchanged) |

Search.py outputs include `sdk_type` in JSON mode. Use `--json` flag for structured output.

## MCP Tools

### Available and Working

| # | Tool | When to Use |
|---|------|-------------|
| 1 | `get_sdk_reference` | Once per conversation — get SDK patterns, expressions, guidelines |
| 2 | `get_suggested_nodes` | During discovery — curated recommendations with usage notes |
| 3 | `validate_workflow` | After EVERY code generation, before deploy |
| 4 | `create_workflow_from_code` | Deploy new workflow |
| 5 | `update_workflow` | Modify existing workflow |
| 6 | `execute_workflow` | Test workflow |
| 7 | `get_execution` | Get test results |
| 8 | `get_workflow_details` | Inspect existing workflow |
| 9 | `publish_workflow` | Activate for production |
| 10 | `unpublish_workflow` | Deactivate |
| 11 | `archive_workflow` | Soft-delete |
| 12 | `search_workflows` | Find existing workflows |
| 13 | `search_projects` | Find projects |
| 14 | `search_folders` | Find folders |

### BROKEN — Do NOT Call

| Tool | Error | Use Instead |
|------|-------|-------------|
| `get_node_types` | "Invalid path - path traversal detected" | `search.py --schema NODE_TYPE` |
| `search_nodes` | 5-result limit, high noise, burns tokens | `search.py "query"` |

## Phase-by-Phase Orchestration

### Phase 1: UNDERSTAND
No tools. Pure conversation — parse intent, classify pattern, confirm with user.

**Exception — existing workflow:**
1. MCP: `search_workflows(query)` → find workflow
2. MCP: `get_workflow_details(workflowId)` → load current state

### Phase 2: DISCOVER

**Sequence (strict order):**

1. **SDK patterns** (once per conversation):
   ```
   MCP: get_sdk_reference(section: "patterns")
   ```

2. **Node discovery** (local DB via search.py):
   For each service/capability the user mentioned:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "slack" --no-tool-variants --limit 10
   ```
   For intent-based discovery (e.g., "I need to notify people"):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "notification" --no-tool-variants --core-only --limit 20
   ```

3. **Technique suggestions** (MCP, supplements local search):
   ```
   MCP: get_suggested_nodes(categories: ["notification", "chatbot", ...])
   ```

4. **Properties schema** for every selected node:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --schema nodes-base.slack --resource message --operation post
   ```

5. **Real-world examples** (optional, for complex nodes):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --template-configs nodes-base.slack
   ```

**For complex workflows (9+ nodes, 3+ service categories):**
Spawn 2-4 `n8n-node-researcher` agents IN PARALLEL, each covering a functional domain. Each agent uses search.py for its domain. Wait for ALL agents to complete before proceeding. Max 4 concurrent agents (DB handles it fine, <100ms per query).

**Maintain a node inventory** through Phase 2 that carries into Phase 3-4:
```
{node_role}: {
  db_type: "nodes-base.slack",
  sdk_type: "n8n-nodes-base.slack",
  version: "2.4",
  resource: "message",
  operation: "post",
  key_params: [...],
  credentials: [...]
}
```

### Phase 3: DESIGN
No tools. Compose blueprint from node inventory. Before presenting, mentally trace the SDK connection chain to verify it's implementable.

### Phase 4: BUILD

1. **SDK guidelines** (once per conversation):
   ```
   MCP: get_sdk_reference(section: "guidelines")
   MCP: get_sdk_reference(section: "design")
   ```

2. **Generate code** using:
   - SDK patterns from Phase 2 step 1
   - Property schemas from Phase 2 step 4 (NOT from get_node_types)
   - Node inventory from Phase 2

   **Simple (≤8 nodes):** Write code directly.
   **Complex (9+ nodes):** Spawn `n8n-code-writer` agent with: blueprint + property schemas + SDK reference. Agent writes code AND self-validates. Returns validated code or remaining errors.

### Phase 5: VALIDATE

```
MCP: validate_workflow(code)
```

**Escalation tiers:**
- **Tier 1 (silent):** Fix and re-validate, up to 3 rounds
- **Tier 2 (agent):** Spawn `n8n-validator` with code + errors, up to 5 rounds
- **Tier 3 (user):** After total 8 failed attempts, show specific errors and ask user

### Phase 6: DEPLOY

```
MCP: create_workflow_from_code(code, description, projectId?, folderId?)
```
or
```
MCP: update_workflow(workflowId, code)
```

Optional project/folder lookup: `search_projects` → `search_folders`
Optional activation: `publish_workflow(workflowId)`

### Phase 7: TEST

```
MCP: execute_workflow(workflowId, inputs, executionMode: "manual")
MCP: get_execution(workflowId, executionId)
```

### Phase 8: ITERATE
Mix of local DB (new node discovery) and MCP (validate, update, execute) based on change scope.

## Claude-in-the-Middle Orchestration (Wait Node Pattern)

When Claude needs to be a processing step INSIDE a single n8n workflow:

### Step 1: Build the workflow with a Wait node
Include a Wait node configured with `resume: 'webhook'` and `httpMethod: 'POST'`.

### Step 2: Execute the workflow
```
MCP: execute_workflow(workflowId, executionMode: "manual")
→ Returns: { executionId, status: "waiting" }
```

### Step 3: Read the paused execution data
```
MCP: get_execution(workflowId, executionId, includeData: true)
→ Read: resultData.runData["Prepare Node"][0].data.main[0][0].json
→ Read: executionData.nodeExecutionStack[0].metadata.resumeUrl
```

### Step 4: Claude analyzes (free AI reasoning)
Read the collected data, think about it, produce structured output.

### Step 5: Resume the workflow
```bash
curl -s -X POST "RESUME_URL" \
  -H "Content-Type: application/json" \
  -d '{"field1": "value1", "field2": "value2"}'
```

### Step 6: Read the final result
```
MCP: get_execution(workflowId, executionId, includeData: true, nodeNames: ["Final Node"])
→ The final node has BOTH n8n data and Claude's analysis
```

### Expression paths after Wait node resumes:
- Pre-Wait data: `$("Node Before Wait").item.json.field`
- Claude's POST body: `$json.body.field`

## Reserved Variable Names

The n8n SDK validator sandboxes code execution. These JavaScript globals are BLOCKED as variable names:

| Blocked Name | Use Instead |
|-------------|-------------|
| `process` | `processData`, `processItems`, `dataProcessor` |
| `fetch` | `fetchData`, `fetchItems`, `dataFetcher` |
| `require` | N/A (not needed in SDK) |
| `eval` | N/A (not needed in SDK) |
| `Function` | N/A (not needed in SDK) |

Always use descriptive, unique variable names. Never reuse SDK builder function names (`node`, `trigger`, `merge`, `tool`, `memory`, etc.) as variable names.

## n8n Runtime Behaviors (Critical for Code Nodes)

These behaviors affect how data flows at runtime. Getting them wrong causes silent data loss.

### HTTP Request returns JSON array → n8n splits into separate items
When an HTTP Request node receives a JSON array (e.g., `[1, 2, 3]`), n8n splits EACH element into a separate item. So `$input.first().json` is just `1` (the first element), NOT the array.

**Wrong:** `const ids = $input.first().json;` → gets just one number
**Right:** `const allItems = $input.all(); const ids = allItems.map(i => i.json);` → reconstructs the array

### Output property must always be array of objects
The SDK `output` property must be `[{ key: value }]`. Bare values like `[42]` or `["text"]` cause validation errors ("Cannot use 'in' operator").

**Wrong:** `output: [47603657, 47610943]`
**Right:** `output: [{ value: 47603657 }, { value: 47610943 }]`

### Set node `include: 'none'` may trigger warning
Some Set node configurations warn about `include` needing expression format. Omit `include` entirely to avoid this — the default (`'all'`) works in most cases. Only use `include: 'none'` when you explicitly want to discard all input fields.

### executeOnce for independent sources
When two nodes are chained and the first returns N items, the second runs N times. If the second is an independent data source (not processing items from the first), add `executeOnce: true` to run it only once regardless of input count.

## Node Position Layout

| Nodes | Layout Strategy |
|-------|----------------|
| 1-5 | Single row: `[240+i*300, 300]` |
| 6-10 | Two rows: `[240+i*300, 200]` top, `[240+i*300, 500]` bottom |
| 10+ | Grid: `[240+(i%4)*300, 200+(i//4)*250]` |
| Branches | True path: y=200, False path: y=500 |
| Parallel | Top branch: y=150, Bottom branch: y=450, Merge: y=300 |
| AI subnodes | LLM/Memory/Tools: 200px below parent agent |
| Error handlers | Same x as source node, y+300 |
| Sticky notes | `[x-100, y-200]` relative to the first node group |
