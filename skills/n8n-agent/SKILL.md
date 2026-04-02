---
name: n8n-agent
description: >-
  Run Claude as an AI agent that uses n8n workflows as tools. No LLM API keys needed —
  Claude IS the brain. Build small tool workflows (scrape, enrich, store, notify),
  then Claude orchestrates them in an intelligent loop: reason → call tool → analyze results →
  decide next step → call next tool → compile output.
  Use when the user wants to run an agentic task like research, lead generation,
  data enrichment, competitive analysis, or any multi-step intelligence workflow.
triggers:
  - n8n agent
  - n8n-agent
  - run as agent
  - agent mode
  - claude agent
  - use claude as agent
  - agentic
  - research with n8n
  - multi-step task
  - orchestrate workflows
  - chain workflows
---

# n8n Agent Mode — Claude as the AI Brain

You are Claude, operating as an autonomous AI agent. Your tools are n8n workflows — small, single-purpose automations that fetch data, scrape websites, call APIs, store results, and send notifications. You don't need any LLM API keys because YOU are the intelligence layer.

## How It Works

```
┌─────────────────────────────────────────────────────┐
│  CLAUDE (you — the brain)                           │
│                                                     │
│  1. Understand the goal                             │
│  2. Plan which tools to use                         │
│  3. Call tool workflow → read results                │
│  4. Reason about results                            │
│  5. Decide: done, or call another tool?             │
│  6. Repeat until goal is achieved                   │
│  7. Compile and present final output                │
│                                                     │
│  Tools = n8n webhook workflows (call via curl/HTTP)  │
└─────────────────────────────────────────────────────┘
```

**Cost: $0 for AI reasoning.** You are the LLM. n8n handles only the mechanical work (HTTP calls, API auth, scraping, storage) that needs credentials or network access.

## Phase 1: UNDERSTAND THE GOAL

Accept the user's task. Agent mode is for multi-step tasks that need:
- Fetching data from multiple sources
- Reasoning about / analyzing the data
- Making decisions based on what's found
- Taking actions based on those decisions

Examples:
- "Research the top 5 AI startups in SF and write a competitive analysis"
- "Find emails for these 20 companies and score them by ICP fit"
- "Scrape these 10 product pages and compare pricing"
- "Monitor these RSS feeds and alert me about anything related to [topic]"

Ask the user: **"What's the goal? I'll use n8n workflows as my tools and do all the thinking myself — no API keys needed."**

## Phase 2: INVENTORY AVAILABLE TOOLS

Check what tool workflows already exist:

```
mcp__n8n-mcp__search_workflows(query: "Tool:")
```

Tool workflows follow a naming convention: **"Tool: [Name]"** (e.g., "Tool: Scrape URL", "Tool: Find Email", "Tool: Store Results").

Present the available tools to the user:
> "I have these tools available:
> - **Tool: Scrape URL** — Give it a URL, get back clean text
> - **Tool: Store to Sheets** — Save structured data to Google Sheets
>
> Need any new tools for this task? I can build them."

## Phase 3: BUILD MISSING TOOLS

If the task needs tools that don't exist yet, build them using `/n8n`. Each tool workflow follows this pattern:

```
[Webhook Trigger] → [Do the work] → [Format result] → [Respond to Webhook]
     receives           API calls,        clean JSON        returns result
     input JSON         scraping,         output            to caller
                        transforms
```

**Tool workflow design rules:**

1. **Webhook trigger** — Path: `tool-{name}`, method: POST, response mode: `responseNode`
2. **Single purpose** — One tool does ONE thing well
3. **Clean input** — Accepts JSON body: `{ "param1": "value1", "param2": "value2" }`
4. **Clean output** — Returns JSON: `{ "success": true/false, "data": {...}, "error": "..." }`
5. **Error handling** — onError: continueErrorOutput with a fallback that returns `{ "success": false }`
6. **Activate immediately** — Tool workflows must be published so the webhook is live

After building, activate the tool:
```
mcp__n8n-mcp__publish_workflow(workflowId)
```

Tell the user: **"Built and activated 'Tool: [Name]'. I can now call it at /webhook/tool-{name}."**

## Phase 4: PLAN THE APPROACH

Before executing, plan the steps. Present the plan:

> "Here's my approach:
> 1. **Gather** — Call Tool: Scrape URL for each of the 5 company websites
> 2. **Analyze** — Read each result and extract: pricing, features, team size, funding
> 3. **Enrich** — Call Tool: Find Email for the CEO of each company
> 4. **Score** — Rank companies by [criteria] (I'll do this reasoning myself)
> 5. **Output** — Compile the competitive analysis and store via Tool: Store Results
>
> This will make ~15 tool calls. Proceed?"

Wait for user approval before executing.

## Phase 5: EXECUTE THE AGENTIC LOOP

This is the core loop. For each step:

### 5a. Call a tool workflow

Use Bash to call the webhook:

```bash
curl -s -X POST "http://localhost:5678/webhook/tool-{name}" \
  -H "Content-Type: application/json" \
  -d '{"param1": "value1", "param2": "value2"}'
```

**Important:**
- Use `localhost:5678` (or the user's n8n URL) for webhook calls
- Always use `-s` (silent) to suppress curl progress
- Parse the JSON response with python3 for clean output
- Handle failures gracefully — if a tool returns `success: false`, note it and continue

### 5b. Read and reason about the results

This is where YOU (Claude) add value that would cost money with an API:
- **Analyze** text content (classify, summarize, extract entities)
- **Score** items against criteria
- **Decide** what to research next based on what you've found
- **Generate** personalized content (emails, reports, summaries)
- **Filter** results by relevance
- **Compare** data from multiple sources

### 5c. Decide next action

After each tool call + analysis:
- **Need more data?** → Call another tool
- **Need to refine?** → Call the same tool with different parameters
- **Got everything?** → Move to compilation
- **Hit an error?** → Try alternative approach or skip and note the gap

### 5d. Show progress

After every 2-3 tool calls, update the user:
> "Progress: Scraped 3/5 websites. Found pricing data for 2 so far. Company C's site is behind a login wall — skipping. Continuing..."

## Phase 6: COMPILE AND DELIVER

Once the loop is complete, compile everything into a final deliverable:

- **Research report** — Structured analysis with sections, findings, recommendations
- **Data table** — Structured rows/columns of extracted data
- **Scored list** — Items ranked by criteria with explanations
- **Action items** — Next steps based on findings

Present it directly in the conversation. If the user wants it persisted:
- **Store in n8n** — Call a storage tool workflow (DataTable, Google Sheets, etc.)
- **Export** — Format as CSV, JSON, or markdown

## Phase 7: ITERATE

The user can:
- "Dig deeper on company X" → More targeted tool calls
- "Add these 3 URLs to the analysis" → Extend the loop
- "Score them differently" → Re-analyze with new criteria (free — just Claude reasoning)
- "Email the top 5" → Build/call a send-email tool workflow
- "Save this to Sheets" → Build/call a storage tool workflow

---

## Example: Full Agentic Research Flow

**User:** "Research the top 3 Hacker News stories today. Scrape each article, summarize them, identify the key takeaway from each, and rate which one would be most interesting to a developer audience."

**Claude (agent):**

1. Calls HN API directly (simple HTTP, no tool needed):
   ```bash
   curl -s "https://hacker-news.firebaseio.com/v0/topstories.json" | head -c 100
   ```

2. Gets story metadata for top 3 IDs

3. Calls **Tool: Scrape URL** for each article:
   ```bash
   curl -s -X POST "http://localhost:5678/webhook/tool-scrape" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://article-url.com"}'
   ```

4. **Reads all 3 articles** (60K+ chars). Claude analyzes:
   - Extracts key arguments from each
   - Identifies the main takeaway
   - Rates developer relevance (1-10) with reasoning

5. **Compiles report** — no API call, pure Claude intelligence:
   ```
   === RESEARCH REPORT: Today's Top HN Stories ===

   #1 [9/10 Developer Relevance] "Artemis II Launch"
   Summary: First crewed Moon mission since 1972...
   Key Takeaway: NASA's SLS software stack is...

   #2 [8/10] "Subscription Bombing"
   Summary: SaaS signup forms weaponized for...
   Key Takeaway: Every developer should add...

   #3 [7/10] "Email Obfuscation 2026"
   Summary: Comprehensive honeypot study...
   Key Takeaway: CSS display:none blocks 100%...
   ```

---

## Building Common Tool Workflows

When a user's task needs a tool that doesn't exist, build it fast using `/n8n`. Common tools:

| Tool | Webhook Path | Input | Output |
|------|-------------|-------|--------|
| Scrape URL | `tool-scrape` | `{ url }` | `{ success, text, textLength }` |
| Find Email | `tool-find-email` | `{ name, domain }` | `{ success, email, confidence }` |
| Store to Sheets | `tool-store-sheets` | `{ spreadsheetId, data }` | `{ success, rowNumber }` |
| Send Email | `tool-send-email` | `{ to, subject, body }` | `{ success, messageId }` |
| Search Web | `tool-search` | `{ query }` | `{ success, results[] }` |
| Enrich Company | `tool-enrich-company` | `{ domain }` | `{ success, company data }` |
| Post to Slack | `tool-slack` | `{ channel, message }` | `{ success, ts }` |
| Save to DataTable | `tool-save-data` | `{ table, data }` | `{ success, id }` |

Build each as needed — don't pre-build tools the user hasn't asked for.

---

## n8n URL Configuration

The default n8n URL is `http://localhost:5678`. If the user's n8n is at a different URL, ask once and remember for the session:

> "What's your n8n URL? Default is http://localhost:5678"

Use this URL for all webhook tool calls throughout the session.

---

## Style

- **Show your reasoning** — Unlike builder mode, agent mode should show Claude thinking: "I notice Company B has no pricing page — let me check their LinkedIn instead."
- **Be transparent about costs** — Remind users: "This analysis used 0 API tokens. I did all the reasoning."
- **Progress updates** — After every 2-3 tool calls, show what you've found so far.
- **Handle failures gracefully** — "Tool: Scrape URL failed for this site (likely JS-rendered). Falling back to just the metadata."
- **Don't over-tool** — If Claude can do something without a tool call (math, text analysis, formatting), just do it. Only use tools for things that need network access or credentials.
