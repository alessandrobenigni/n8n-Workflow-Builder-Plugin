<p align="center">
  <img src="https://raw.githubusercontent.com/n8n-io/n8n/master/assets/n8n-logo.png" alt="n8n" width="120" />
</p>

<h1 align="center">n8n Workflow Builder</h1>

<p align="center">
  <strong>The most advanced n8n workflow plugin for Claude Code.</strong><br/>
  7 commands. 1,396 nodes. 22 workflow patterns. Zero guesswork.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#commands">Commands</a> &bull;
  <a href="#-claude-as-your-ai-brain">Agent Mode</a> &bull;
  <a href="#-claude-in-the-middle">Middleware</a> &bull;
  <a href="#examples">Examples</a> &bull;
  <a href="#architecture">Architecture</a>
</p>

---

## Why This Plugin Exists

Building n8n workflows manually means clicking through hundreds of nodes, guessing parameter names, and debugging connections. This plugin turns that into a conversation.

**But that's just the beginning.** Here's what makes it different:

### 1. Claude IS Your AI Brain — $0 LLM Cost

Traditional n8n AI Agent node requires an LLM API key (OpenAI, Anthropic) and charges per token. With this plugin, **Claude does all the reasoning for free** — n8n just handles the mechanical work.

```
You: /n8n-agent research the top 5 AI startups in SF, scrape their websites,
     find CEO emails, score by ICP fit, and draft personalized outreach emails

Claude: *builds tool workflows* → *calls them* → *reads results* →
        *scores leads* → *writes emails* → *stores everything*

Total AI cost: $0.00 (Claude did all the thinking)
```

### 2. Claude-in-the-Middle — One Workflow, Claude as a Node

Claude can be a **processing step inside a single n8n workflow execution**. The workflow runs, pauses at a Wait node, Claude analyzes the data and POSTs back, the workflow resumes with Claude's intelligence merged in.

```
[Trigger] → [Collect Data] → [WAIT] → [Use Claude's Analysis] → [Take Action]
                                ↑
                           Claude reads
                           paused data,
                           thinks for free,
                           POSTs JSON back
```

One execution ID. One workflow in n8n. Claude in the middle. $0.

### 3. Credentials Created From Conversation

Paste your API key in the chat. The plugin creates the credential in n8n via REST API. No switching to the browser for API-key services.

```
Plugin: "Your workflow needs OpenAI. Paste your API key:"
You:     sk-proj-abc123...
Plugin:  "Created 'OpenAI' credential in n8n. Assigned to workflow."
```

### 4. 1,396 Nodes — Searched Instantly, Zero Tokens

A 75MB local SQLite database with every n8n node, pre-tagged by intent. Say "send notification" and it instantly finds Slack, Gmail, Telegram, Discord, Teams, WhatsApp, and 40+ more. No MCP round-trips. No token cost. Instant.

### 5. Enterprise Patterns Built In

- **22 workflow patterns** — linear, branching, parallel, batch, AI agent, RAG, multi-trigger, error handling, sub-workflow, forms, dedup, diff, approval flows, audit trails
- **5 error handling templates** — retry with backoff, dead letter queue, circuit breaker, alerts, graceful degradation
- **7 stateful patterns** — cross-execution dedup, change detection, persistent state, human-in-the-loop approval, incremental sync, audit logging, multi-step forms
- **Security audit** — 17-check graded report (A-F) for any workflow

### 6. Full Lifecycle — Build, Test, Document, Audit, Manage

Not just a builder. A complete toolkit:

| Command | What It Does |
|---------|-------------|
| `/n8n` | Build any workflow from plain English |
| `/n8n-agent` | Use Claude as AI brain with n8n tool workflows |
| `/n8n-test` | Define test cases, run, compare expected vs actual |
| `/n8n-docs` | Auto-generate markdown documentation |
| `/n8n-audit` | Security + best practices audit (A-F grade) |
| `/n8n-manage` | List, activate, execute, analyze performance |
| `/n8n-browse` | Explore all 1,396 nodes, patterns, and templates |

### 7. Beginner Friendly, Expert Capable

First time? The plugin detects it, offers 5 starter templates, and explains every concept inline. Power user? Skip straight to "build a 17-node RAG pipeline with vector stores and human approval."

---

## See It In Action

```
/n8n send me a Slack message every morning at 9am with the weather forecast
```

That's it. You type what you want, and the plugin:

1. Finds the right nodes from 1,396 options (instant, local DB)
2. Shows you a visual blueprint for approval
3. Generates validated SDK code with exact parameter names
4. Creates any needed credentials (asks you for API keys inline)
5. Deploys to your n8n instance
6. Activates and tests it

Works for everything from 2-node automations to 17-node parallel scraping pipelines with error handling and human approval flows.

---

## Quick Start

### Step 1: Install and Launch n8n

If you don't have n8n running yet:

```bash
# Using Docker (recommended)
docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n

# Or using npm
npx n8n start
```

Open your browser to **http://localhost:5678** and complete the initial setup (create your owner account).

### Step 2: Enable the MCP Server in n8n

The plugin communicates with n8n through its built-in MCP (Model Context Protocol) server. You need to enable it:

1. **Open n8n** in your browser at `http://localhost:5678`
2. Click your **avatar/initials** in the bottom-left corner
3. Click **Settings**
4. In the left sidebar, click **MCP Server** (under "Instance-level")
5. Toggle **MCP Server** to **Enabled**
6. You'll see the MCP connection details:
   - **URL:** `http://localhost:5678/mcp-server/http`
   - **Bearer Token:** A long JWT token (starts with `eyJ...`)
7. **Copy the Bearer Token** — you'll need it in the next step

> **Important:** The MCP Server section only appears in n8n version 1.76+ with the MCP feature enabled. If you don't see it, update n8n or check the [n8n MCP documentation](https://docs.n8n.io/hosting/configuration/environment-variables/#mcp).

### Step 3: Configure Credentials

You need two files in your project directory:

**A. `.env` file** — Stores your n8n connection details:

```env
# n8n instance URL (default: http://localhost:5678)
N8N_URL=http://localhost:5678

# n8n API Key — needed for credential management
# Get it from: n8n Settings > API > Create API Key
N8N_API_KEY=your-api-key-here
```

The API key enables the plugin to **create credentials automatically** (e.g., OpenAI, Anthropic, Stripe API keys) without you needing to open the n8n UI. OAuth credentials (Slack, Gmail) still require browser-based setup — the plugin will guide you step by step.

**B. `.mcp.json` file** — Connects Claude Code to n8n's MCP server:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "type": "http",
      "url": "http://localhost:5678/mcp-server/http",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN_HERE"
      }
    }
  }
}
```

Replace `YOUR_MCP_TOKEN_HERE` with the Bearer Token from n8n Settings > MCP Server.

> **Why two credentials?** The MCP token (Bearer) gives Claude access to build and manage workflows. The API key (`X-N8N-API-KEY`) gives access to the n8n REST API for credential management, which the MCP server doesn't support. Both are from your n8n instance, but they're different tokens.

**Verify the connection:** Open Claude Code and type:
```
Can you call get_sdk_reference and confirm n8n MCP is working?
```

If Claude responds with SDK documentation, the connection is working.

### Step 4: Install the Plugin

In Claude Code, run these two commands:

```bash
# Step 1: Add the marketplace
/plugin marketplace add TheSauceSuite/n8n-plugin

# Step 2: Install the plugin
/plugin install n8n-workflow-builder@n8n-marketplace
```

> **REQUIRED:** [Git LFS](https://git-lfs.com/) must be installed BEFORE installing the plugin. The 75MB node database won't download without it.
> - **Mac:** `brew install git-lfs && git lfs install`
> - **Linux:** `apt install git-lfs && git lfs install`
> - **Windows:** Download from [git-lfs.com](https://git-lfs.com/), then run `git lfs install`
>
> If you already installed without Git LFS, run `git lfs pull` in the plugin directory to download the database.

### Step 5: Start Building

```
/n8n send me a Slack message every morning at 9am
```

That's all you need. The plugin handles everything from here.

---

## Commands

### `/n8n` — Build Workflows

The main command. Handles creating, updating, and iterating on workflows.

```bash
# Simple automations
/n8n send a Slack message to #general every Monday at 9am
/n8n when I receive a Gmail, save attachments to Google Drive
/n8n create a webhook that logs incoming data to a Google Sheet

# Data pipelines
/n8n every hour, fetch new HubSpot contacts, enrich with Clearbit, update Salesforce
/n8n sync Airtable records to Postgres every 15 minutes
/n8n when a Stripe payment succeeds, create an invoice in QuickBooks and email receipt

# AI workflows
/n8n build a chatbot that answers questions about our company docs
/n8n create an AI agent that can search emails, check calendar, and send Slack messages
/n8n when a support ticket arrives in Zendesk, classify priority with AI and route to the right team

# Complex patterns
/n8n webhook receives order → check inventory (if in stock: process + notify, else: backorder + alert)
/n8n scrape 100 URLs, extract product data, deduplicate, and store in MongoDB
/n8n multi-step form: collect info → AI validates → human approves → create account
```

After deployment, keep talking to modify:
```
Now add error handling to the HTTP request
Change the Slack channel to #alerts
Add a filter to only process orders above $100
Activate it
Run a test
```

### `/n8n-agent` — Agent Mode (Claude as AI Brain)

Use Claude as an autonomous AI agent with n8n workflows as tools. **No LLM API keys needed** — Claude does all the reasoning, analysis, and decision-making. n8n handles the mechanical work (scraping, API calls, storage, notifications).

```bash
# Research tasks
/n8n-agent research the top 5 AI startups in SF and write a competitive analysis
/n8n-agent scrape these 10 product pages and compare their pricing

# Lead generation
/n8n-agent find emails for these 20 companies and score them by ICP fit
/n8n-agent scrape LinkedIn profiles for AI engineers at FAANG companies

# Data analysis
/n8n-agent monitor these RSS feeds and alert me about AI regulation news
/n8n-agent analyze the top HN stories today and rate developer relevance

# Multi-step workflows
/n8n-agent for each company in this list: scrape their website, find the CEO's email, draft a personalized outreach email, and save everything to Google Sheets
```

Claude builds small "tool workflows" as needed (webhook-triggered n8n workflows), then orchestrates them in a reasoning loop — calling tools, reading results, analyzing, deciding next steps.

### `/n8n-manage` — Manage Workflows

List, inspect, activate, deactivate, archive, and execute existing workflows.

```bash
/n8n-manage list my workflows
/n8n-manage activate the lead enrichment workflow
/n8n-manage run the daily report workflow
/n8n-manage deactivate workflow abc123
/n8n-manage archive the old sync workflow
```

### `/n8n-browse` — Explore Capabilities

Discover what n8n can do before committing to building.

```bash
/n8n-browse what nodes are available for Slack?
/n8n-browse what triggers can start a workflow?
/n8n-browse show me all AI agent nodes
/n8n-browse what patterns work for data pipelines?
/n8n-browse give me workflow ideas for sales automation
```

---

## How It Works

### The 8-Phase Flow

Every `/n8n` command goes through up to 8 phases. Simple workflows breeze through in 2-3 exchanges. Complex ones get the full treatment.

#### Phase 1: Understand
The plugin parses your request — extracts services, triggers, actions, conditions, and data flow. It classifies the workflow pattern (linear, branching, parallel, AI agent, etc.) and confirms understanding with you.

#### Phase 2: Discover
Searches the **local SQLite database** (1,396 nodes) to find the exact nodes needed. For each node, it retrieves the full property schema (parameter names, types, defaults, options) and optionally finds real-world configuration examples from 2,737 workflow templates.

For complex workflows (9+ nodes), **parallel research agents** (up to 4) discover nodes simultaneously across functional domains.

#### Phase 3: Design
Presents a visual **workflow blueprint** — an ASCII flow diagram with node details, data flow, and credential requirements — for your approval.

```
WORKFLOW: Morning Lead Enrichment
PATTERN: Scheduled linear chain

[Schedule Trigger] ──→ [HubSpot: Get Leads] ──→ [Clearbit: Enrich] ──→ [Slack: Post Summary]
     9 AM daily          contact/getAll           lookup by email          #sales-leads
```

#### Phase 4: Build
Generates complete n8n Workflow SDK code using **exact parameter names** from the database. For complex workflows, a dedicated **Opus-powered code writer agent** handles generation.

#### Phase 5: Validate
Automatically validates the generated code via the MCP server. If validation fails, a **3-tier escalation** handles it:
1. **Auto-fix** (silent) — Fixes common issues, re-validates up to 3 rounds
2. **Validator agent** — Systematically diagnoses and fixes using the node database, up to 5 rounds
3. **User escalation** — After 8 total attempts, shows you the specific remaining issues

#### Phase 6: Deploy
Creates the workflow in your n8n instance. Optionally places it in a specific project/folder and activates it for production.

#### Phase 7: Test
Runs a test execution with appropriate inputs (chat message, webhook payload, form data, or manual trigger) and shows you the results node by node.

#### Phase 8: Iterate
The conversation stays open. Say "now add X", "change Y", or "remove Z" and the plugin loops back to the right phase — no starting over.

---

## Hybrid Architecture

The plugin uses two complementary systems:

### Local SQLite Database (ships with plugin)

The `data/nodes.db` file (75MB, Git LFS) contains:

| Data | Count | Purpose |
|------|-------|---------|
| Nodes | 1,396 | 812 core + 584 community, with full property schemas |
| Property definitions | 22.3 MB | Exact parameter names, types, defaults, options |
| Semantic tags | 5.1 avg/node | Pre-computed intent tags for zero-token search |
| Workflow templates | 2,737 | Real-world workflows with complete JSON |
| Template configs | 215 | Proven parameter configurations from popular templates |
| FTS5 index | Built-in | Full-text search across names, descriptions, docs, operations |

**Why local?** Node discovery is instant, unlimited, and burns zero tokens. When you say "send notification", the tag `notification` instantly matches Slack, Gmail, Telegram, Discord, Teams, Twilio, PagerDuty, and 40+ more — in one SQL query.

### n8n MCP Server (your running instance)

The MCP connection handles everything that touches your live n8n:

| Capability | MCP Tool |
|------------|----------|
| SDK reference docs | `get_sdk_reference` |
| Curated node recommendations | `get_suggested_nodes` |
| Validate workflow code | `validate_workflow` |
| Create workflow | `create_workflow_from_code` |
| Update workflow | `update_workflow` |
| Execute workflow | `execute_workflow` |
| Get execution results | `get_execution` |
| Inspect workflow | `get_workflow_details` |
| Activate/deactivate | `publish_workflow` / `unpublish_workflow` |
| Archive | `archive_workflow` |
| Search workflows | `search_workflows` |
| Manage projects/folders | `search_projects` / `search_folders` |

---

## Agent Mode

### The Paradigm Shift

Traditional approach: n8n's AI Agent node calls an LLM API (OpenAI, Anthropic) → **costs money per token**.

Agent Mode: **Claude IS the AI brain** → n8n workflows are just tools → **$0 for all AI reasoning**.

```
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE CODE (the brain — free)                             │
│                                                             │
│  "Research AI startups in SF, find CEO emails, score them"  │
│                                                             │
│  Claude reasons → picks a tool → calls it → reads result    │
│  → reasons again → picks next tool → calls it → ...         │
│  → compiles final analysis with scoring and recommendations │
│                                                             │
│  Tools (each is a small n8n webhook workflow):               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ Scrape URL │ │ Find Email │ │ Store Data │             │
│  │  (n8n wf)  │ │  (n8n wf)  │ │  (n8n wf)  │             │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘             │
│        ▼               ▼               ▼                    │
│   HTTP POST        HTTP POST       HTTP POST                │
│   to webhook       to webhook      to webhook               │
└────────┼───────────────┼───────────────┼────────────────────┘
         ▼               ▼               ▼
   ┌─────────────────────────────────────────────┐
   │              n8n INSTANCE                    │
   │  Workflow: "Tool: Scrape URL"               │
   │  [Webhook] → [Jina Reader] → [Respond]     │
   │                                             │
   │  Workflow: "Tool: Find Email"               │
   │  [Webhook] → [Findymail API] → [Respond]   │
   │                                             │
   │  Workflow: "Tool: Store to Sheets"          │
   │  [Webhook] → [Google Sheets] → [Respond]   │
   └─────────────────────────────────────────────┘
```

### How It Works

1. **You describe the task** — "Research these 5 companies and score them"
2. **Claude inventories available tools** — checks which tool workflows exist
3. **Builds missing tools** — creates new webhook workflows via `/n8n` if needed
4. **Plans the approach** — shows you the step-by-step plan
5. **Executes the loop** — calls tools, reads results, reasons, decides next step
6. **Compiles the output** — produces a final report, analysis, or dataset

### What Claude Does vs What n8n Does

| Task | Who | Cost |
|------|-----|------|
| Decide what to research | **Claude** (reasoning) | $0 |
| Scrape a website | **n8n** (HTTP + Jina Reader) | $0 |
| Read and understand article text | **Claude** (comprehension) | $0 |
| Call a paid API (Findymail, Clearbit) | **n8n** (HTTP + auth) | API cost only |
| Score leads by ICP fit | **Claude** (analysis) | $0 |
| Generate personalized email copy | **Claude** (writing) | $0 |
| Send the email | **n8n** (Gmail/SendGrid) | $0 |
| Store results in a spreadsheet | **n8n** (Google Sheets) | $0 |

### Tool Workflow Pattern

Each tool is a small n8n workflow:

```
[Webhook Trigger] → [Do the work] → [Format JSON] → [Respond to Webhook]
    POST input         API call,        { success,       returns result
    { param: val }     scrape, etc.      data, error }   to Claude
```

Tools are named with a `Tool:` prefix and called via HTTP:
```bash
curl -s -X POST "http://localhost:5678/webhook/tool-scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Example: Agentic Research Session

```
You: /n8n-agent analyze today's top 3 Hacker News stories, scrape each article,
     and rate which is most relevant for a developer audience

Claude: I'll use Tool: Scrape URL to fetch each article, then analyze them myself.

  Step 1: Fetching HN top stories... [direct API call]
  → Got 3 stories: Artemis II (868pts), Subscription Bombing (110pts), Email Obfuscation (59pts)

  Step 2: Scraping article 1/3... [calling Tool: Scrape URL]
  → Got 39,464 chars from NASA

  Step 3: Scraping article 2/3... [calling Tool: Scrape URL]
  → Got 9,037 chars from Bytemash

  Step 4: Scraping article 3/3... [calling Tool: Scrape URL]
  → Got 19,185 chars from spencermortensen.com

  Step 5: Analyzing all 67,686 chars of article text...

  === RESEARCH REPORT ===

  #1 [8/10 Developer Relevance] "Subscription Bombing"
  Key Takeaway: Your signup form is a weapon — attackers use it to
  spam-bomb victims. Add CAPTCHA and rate limiting today.

  #2 [7/10] "Email Obfuscation 2026"
  Key Takeaway: CSS display:none blocks 100% of harvesters. Simple works.

  #3 [6/10] "Artemis II Launch"
  Key Takeaway: Engineering marvel, but less directly actionable for devs.

  Total AI cost: $0.00 (Claude did all reasoning)
  Tool calls: 3 scrapes via n8n
```

---

## Supported Workflow Patterns

The plugin handles every n8n pattern:

| Pattern | Description | Example |
|---------|-------------|---------|
| **Linear chain** | Step-by-step sequence | Schedule → Fetch → Transform → Send |
| **If/Else branching** | Two-way conditional routing | Check amount → High: approve / Low: reject |
| **Switch routing** | Multi-way routing by category | Classify ticket → Urgent / Normal / Low priority |
| **Parallel execution** | Run branches simultaneously, merge results | [Fetch API A + Fetch API B] → Merge → Process |
| **Batch processing** | Loop through items in batches | Fetch 1000 rows → Process 50 at a time → Done |
| **AI Agent** | Autonomous agent with LLM, tools, and memory | Chat → Agent (OpenAI + Calculator + Web Search) → Response |
| **RAG pipeline** | Knowledge base Q&A | Ingest PDFs → Embed → Vector Store + Chat → Retrieve → Answer |
| **Multi-trigger** | Multiple triggers share the same chain | [Webhook + Schedule] → Same processing pipeline |
| **Error handling** | Fallback branches for failures | API Call → Success path / Error → Alert + Retry |
| **Sub-workflow** | Reusable modular workflows | Main → Execute Sub-workflow → Continue |
| **Form-based** | Multi-step form collection | Form Trigger → Page 2 → Page 3 → Process → Respond |
| **Data sync** | Keep two systems in sync | Schedule → Fetch from A → Compare → Update B |
| **Tool workflow** | Single-purpose webhook for agent mode | Webhook → Process → Respond (Claude calls via HTTP) |
| **Claude-in-the-Middle** | Claude as a processing step inside one workflow | Collect → **Wait** → Claude POSTs analysis → Resume → Act |

### Claude-in-the-Middle (Enterprise Pattern)

The most architecturally clean integration: Claude is a processing node **inside** a single n8n workflow execution.

```
┌──────────── SINGLE n8n WORKFLOW EXECUTION ──────────────┐
│                                                          │
│  [Trigger] → [Collect] → [Prepare] → [WAIT] → [Report]  │
│                                         ↑                │
│                                    Claude reads          │
│                                    paused data,          │
│                                    POSTs JSON            │
│                                    analysis back         │
└──────────────────────────────────────────────────────────┘
```

- **One workflow, one execution ID** — clean in n8n's execution history
- **Data flows through Claude** — pre-Wait n8n data + Claude's analysis merge in the final nodes
- **Wait node** pauses execution and exposes a resume URL
- **Claude POSTs JSON** to the resume URL — workflow resumes with Claude's output in `$json.body.*`
- **$0 AI cost** — Claude does all reasoning, n8n handles collection and action

---

## Tag-Based Node Discovery

Every node in the database has pre-computed semantic tags. This enables instant, zero-token retrieval by user intent:

| What You Say | Tag Searched | Nodes Found |
|-------------|-------------|-------------|
| "send notification" | `notification` | Slack, Gmail, Telegram, Discord, Teams, WhatsApp, Twilio, PagerDuty, SendGrid, 40+ more |
| "store in database" | `database` | Postgres, MySQL, MongoDB, Redis, DataTable, BigQuery, Snowflake, DynamoDB, 25+ more |
| "send email" | `email` | Gmail, Outlook, SendGrid, Mailchimp, SES, SMTP, Brevo, ConvertKit, 30+ more |
| "build a chatbot" | `chatbot` | Chat Trigger, AI Agent, Simple Memory, Redis/Postgres Memory, OpenAI Assistant |
| "RAG pipeline" | `rag` | All vector stores, embeddings, retrievers, document loaders, text splitters |
| "project management" | `project-management` | Jira, Linear, Trello, Asana, ClickUp, GitHub, GitLab, Todoist |
| "CRM automation" | `crm` | HubSpot, Salesforce, Pipedrive, Zoho CRM, Copper, ActiveCampaign |
| "scrape website" | `web-scraping` | HTTP Request, HTML Extract, Phantombuster, Airtop, Jina AI |
| "schedule task" | `trigger-on-schedule` | Schedule Trigger, Cron, Interval |
| "e-commerce" | `ecommerce` | Stripe, Shopify, WooCommerce, PayPal, Chargebee |

You can also search by exact service name — "Gmail" finds Gmail, Gmail Tool, and Gmail Trigger instantly.

---

## Node Coverage

The plugin knows about **every n8n node**:

| Category | Count | Examples |
|----------|-------|---------|
| **Core nodes** | 812 | Slack, Gmail, Postgres, HTTP Request, If, Merge, Code, Set... |
| **Community nodes** | 584 | Firecrawl, Airtop, Resend, ElevenLabs, Phantombuster... |
| **Verified community** | 516 | Vetted by n8n team |
| **Trigger nodes** | 166 | Schedule, Webhook, Form, Chat, Email, 60+ app triggers |
| **AI/LangChain nodes** | 99 | 15 LLM providers, 10+ vector stores, 9 embeddings, memory, tools... |
| **Tool variant nodes** | 264 | Every major node has a Tool variant for use inside AI Agents |

### AI/LLM Ecosystem

| Component | Nodes |
|-----------|-------|
| **LLM Providers** | OpenAI, Anthropic, Google Gemini, Ollama, Groq, Mistral, DeepSeek, Cohere, xAI Grok, Azure OpenAI, AWS Bedrock, Google Vertex, Vercel AI Gateway, Hugging Face |
| **Vector Stores** | Pinecone, Qdrant, ChromaDB, Weaviate, Supabase, PGVector, Redis, MongoDB Atlas, Azure AI Search, In-Memory, Zep, Milvus |
| **Embeddings** | OpenAI, Azure OpenAI, Google Gemini, Google Vertex, Ollama, Cohere, Mistral, Hugging Face, AWS Bedrock |
| **Memory** | Simple Buffer, Redis, Postgres, MongoDB, Zep, Motorhead, Xata |
| **AI Tools** | Calculator, Code, Think, HTTP Request, Workflow, Vector Store Q&A, Wikipedia, MCP Client |
| **Chains** | Basic LLM, Summarization, Q&A Retrieval |
| **Processors** | Information Extractor, Text Classifier, Sentiment Analysis, Guardrails |
| **Document Loaders** | Default Data, Binary Input, JSON Input, GitHub |
| **Text Splitters** | Recursive Character, Character, Token |

---

## Architecture

```
n8n-workflow-builder/
├── .claude-plugin/
│   └── plugin.json                    Plugin metadata
│
├── data/
│   ├── nodes.db                       SQLite database (75MB, Git LFS)
│   │                                  1,396 nodes + 2,737 templates + tags + schemas
│   ├── search.py                      Multi-strategy search utility
│   ├── generate_tags.py               Tag generation script
│   └── tag_taxonomy.md                Tag taxonomy documentation
│
├── skills/
│   ├── n8n/
│   │   ├── SKILL.md                   Main skill: /n8n (8-phase workflow builder)
│   │   └── references/
│   │       ├── mcp-orchestration.md   Single source of truth for tool usage
│   │       ├── workflow-patterns.md   16 workflow pattern classifications
│   │       └── blueprint-format.md    Visual design presentation format
│   ├── n8n-agent/
│   │   └── SKILL.md                   Agent mode: /n8n-agent (Claude as AI brain)
│   ├── n8n-manage/
│   │   └── SKILL.md                   Lifecycle management: /n8n-manage
│   └── n8n-browse/
│       └── SKILL.md                   Exploration: /n8n-browse
│
├── agents/
│   ├── n8n-node-researcher.md         Parallel node discovery (Sonnet, local DB)
│   ├── n8n-code-writer.md             SDK code generation (Opus)
│   ├── n8n-tool-builder.md            Tool workflow builder for agent mode (Sonnet)
│   └── n8n-validator.md               Validation fix loop (Sonnet, local DB)
│
├── README.md
├── LICENSE                            MIT
├── .gitattributes                     Git LFS tracking for nodes.db
└── .gitignore
```

### How the Agents Work

| Agent | Model | Purpose | When Spawned |
|-------|-------|---------|--------------|
| **n8n-node-researcher** | Sonnet | Searches local DB for nodes in a specific domain | Complex workflows: 2-4 spawned in parallel |
| **n8n-code-writer** | Opus | Writes complete SDK code from blueprint + schemas | Complex workflows (9+ nodes) |
| **n8n-tool-builder** | Sonnet | Builds webhook tool workflows for agent mode | When /n8n-agent needs a new tool |
| **n8n-validator** | Sonnet | Diagnoses and fixes validation errors using local DB | When auto-fix fails after 3 rounds |

---

## Troubleshooting

### "I can't reach the n8n MCP server"

1. Make sure n8n is running (`http://localhost:5678` loads in your browser)
2. Check that the MCP Server is enabled in n8n Settings → MCP Server
3. Verify your `.mcp.json` has the correct URL and Bearer token
4. The token expires if you regenerate it in n8n — update `.mcp.json` if needed

### "Plugin not found" or "/n8n command not recognized"

1. Verify the plugin is installed: run `/plugin` and check the "Installed" tab
2. Try reinstalling: `/plugin marketplace add TheSauceSuite/n8n-plugin` then `/plugin install n8n-workflow-builder@n8n-marketplace`
3. Restart Claude Code after installing

### "Validation failed" errors

The plugin has a 3-tier auto-fix system. If all 8 attempts fail, it will show you the specific errors. Common causes:
- **Missing credentials** — Configure the required service credentials in n8n before activating
- **Parameter mismatch** — Usually fixed automatically; if not, the error message tells you exactly what's wrong
- **Reserved variable names** — `process`, `fetch`, `require` are blocked by the SDK sandbox

### "nodes.db not found"

The database is tracked with Git LFS. If it shows as a 133-byte pointer file:
```bash
git lfs pull
```

### Updating the node database

The database ships with node data current at plugin release time. To update with the latest n8n nodes:
```bash
# Re-download from the n8n-mcp project
curl -L -o data/nodes.db "https://github.com/czlonkowski/n8n-mcp/raw/main/data/nodes.db"
# Rebuild semantic tags
python3 data/generate_tags.py
```

---

## Configuration

### .env File (Required for Credential Management)

Create a `.env` file in your project root:

```env
# Required: Your n8n instance URL
N8N_URL=http://localhost:5678

# Required for credential management: n8n API key
# Get it from: n8n Settings > API > Create API Key
N8N_API_KEY=your-api-key-here
```

**What the API key enables:**
- List existing credentials (check what's already configured)
- Create API-key credentials automatically (OpenAI, Anthropic, Stripe, etc.)
- Verify credentials exist after setup
- The plugin asks you for the actual API keys/secrets — it just handles creating them in n8n for you

**Without the API key:** The plugin still works for building/deploying/testing workflows. You'll just need to set up credentials manually through the n8n UI (the plugin guides you step by step).

### .mcp.json File (Required for Workflow Management)

**Local n8n (default):**
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "type": "http",
      "url": "http://localhost:5678/mcp-server/http",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

**n8n Cloud:**
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "type": "http",
      "url": "https://YOUR_INSTANCE.app.n8n.cloud/mcp-server/http",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

**Self-hosted n8n (custom domain):**
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "type": "http",
      "url": "https://n8n.yourdomain.com/mcp-server/http",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### Where to Put .mcp.json

| Location | Scope |
|----------|-------|
| `~/.claude/mcp.json` | Global — available in all projects |
| `./mcp.json` (project root) | Project — only available in this directory |

---

## Examples

### Simple: Daily Slack Reminder

```
/n8n every weekday at 9am, post "Good morning team! Time for standup." to #engineering on Slack
```

Result: Schedule Trigger → Slack (post message)

### Medium: Lead Enrichment Pipeline

```
/n8n when a new contact is added to HubSpot, look up their company on Clearbit,
then add the enrichment data back to the HubSpot contact, and post a summary to #sales on Slack
```

Result: HubSpot Trigger → HTTP Request (Clearbit) → HubSpot (update) → Slack (post)

### Complex: AI-Powered Support Triage

```
/n8n when a new Zendesk ticket arrives, use an AI agent to classify its priority
(urgent/high/normal/low) and category (billing/technical/general), then route:
- urgent → Slack alert to #incidents + assign to on-call
- high → assign to senior team
- normal → add to backlog
- low → auto-respond with FAQ link
```

Result: Zendesk Trigger → AI Agent (with Structured Output) → Switch → 4 branches with different actions

### Advanced: RAG Chatbot

```
/n8n build a customer support chatbot that:
1. Has a chat interface
2. Searches our knowledge base (stored in Pinecone) for relevant docs
3. Uses GPT-4 to generate answers based on the retrieved docs
4. Remembers conversation history
5. Falls back to creating a Zendesk ticket if it can't answer
```

Result: Chat Trigger → AI Agent (OpenAI + Pinecone Retriever + Memory + Zendesk Tool)

---

## Contributing

Contributions welcome! Key areas:

- **Tag taxonomy** — Improve semantic tags in `data/generate_tags.py` for better node discovery
- **Workflow patterns** — Add new patterns to `skills/n8n/references/workflow-patterns.md`
- **Node database** — Update `data/nodes.db` with latest n8n releases
- **Agent prompts** — Refine agent instructions in `agents/` for better code generation

```bash
# After modifying tags
python3 data/generate_tags.py

# Test search quality
python3 data/search.py "send notification" --no-tool-variants --core-only
python3 data/search.py --schema nodes-base.slack --resource message --operation post
python3 data/search.py --stats
```

---

## License

MIT — see [LICENSE](LICENSE)

---

<p align="center">
  Built with <a href="https://github.com/czlonkowski/n8n-mcp">n8n-mcp</a> &bull;
  Powered by <a href="https://claude.ai/claude-code">Claude Code</a> &bull;
  Made by <a href="https://github.com/TheSauceSuite">TheSauceSuite</a>
</p>
