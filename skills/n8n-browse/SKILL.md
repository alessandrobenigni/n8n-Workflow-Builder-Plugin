---
name: n8n-browse
description: >-
  Explore n8n capabilities — browse available nodes, discover integrations,
  learn about workflow patterns, and get inspired. Use when the user wants
  to explore what's possible before building.
triggers:
  - n8n browse
  - n8n-browse
  - what nodes are available
  - what can n8n do
  - n8n integrations
  - show me n8n nodes for
  - what triggers are available
  - workflow ideas
  - how do I use
  - n8n patterns
  - n8n capabilities
  - what services does n8n support
---

# n8n Capability Browser

You help users explore what n8n can do — discover nodes, understand patterns, and get inspired.

The local database at `${CLAUDE_PLUGIN_ROOT}/data/nodes.db` contains all 1,396 n8n nodes. Access it via:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py [command]
```

## Determine Exploration Type

| Intent | Type |
|--------|------|
| "what nodes for [service]", "does n8n have [x]" | **Node Search** |
| "what can I do with", "patterns", "techniques" | **Technique Exploration** |
| "how do I use [node]", "what does [node] do" | **Node Details** |
| "ideas", "inspiration", "what can I build" | **Workflow Ideas** |
| "triggers", "what can start a workflow" | **Trigger Discovery** |
| "AI nodes", "agent", "LLM", "vector store" | **AI Exploration** |
| "let's build that" | **Handoff to /n8n** |

## Actions

### Node Search

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py "user's query" --no-tool-variants --limit 15
```

Present grouped by type:
```
**Nodes for "[query]":**

Triggers:
- **Gmail Trigger** (n8n-nodes-base.gmailTrigger) — Polls for new emails

Actions:
- **Gmail** (n8n-nodes-base.gmail) — Send, read, label emails
- **Gmail Tool** (n8n-nodes-base.gmailTool) — Use inside AI Agents
```

### Technique Exploration

Call `mcp__n8n-mcp__get_suggested_nodes` with relevant categories.

Present the pattern hint and recommended nodes with usage notes.

### Node Details

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --node nodes-base.slack
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --schema nodes-base.slack --resource message --operation post
```

Present operations, parameters, credentials, and usage guidance.

### Workflow Ideas

Present organized ideas across categories (productivity, sales, AI, DevOps, etc.) and offer to build any of them with `/n8n`.

### Trigger Discovery

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --list-triggers
```

Present organized by category: time-based, events, app-specific, system triggers.

### AI Exploration

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --list-ai
```

Present the full AI ecosystem: LLM providers, vector stores, embeddings, memory, tools, chains, processors.

### Database Stats

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --stats
```

## Handoff

If user says "let's build that" or shows intent to create, say "Let's build it!" and invoke `/n8n` with the gathered context.
