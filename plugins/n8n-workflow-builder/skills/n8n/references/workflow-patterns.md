# Workflow Pattern Classification Guide

Use this reference to map the user's natural language description to the correct n8n workflow pattern. A workflow may combine multiple patterns (e.g., a scheduled workflow with branching and an AI agent).

## Pattern Detection

### 1. SCHEDULED / LINEAR CHAIN
**Signal words:** "every", "daily", "hourly", "weekly", "on a schedule", "at [time]", "cron", "recurring", "periodically", "each morning/evening"
**Pattern:** Schedule Trigger → Step 1 → Step 2 → ... → Final Step
**Key nodes:** `n8n-nodes-base.scheduleTrigger` (v1.3)
**SDK pattern:** `.add(trigger).to(nodeA).to(nodeB).to(nodeC)`
**CRITICAL:** Scheduled workflows MUST be published (activated) to fire on schedule. A draft will NOT run.

**Common schedule configurations:**

| User Says | Config |
|-----------|--------|
| "every morning at 9" | `field: 'cronExpression', expression: '0 9 * * *'` |
| "every hour" | `field: 'hours', hoursInterval: 1` |
| "every 5 minutes" | `field: 'minutes', minutesInterval: 5` |
| "every weekday at 9am" | `field: 'cronExpression', expression: '0 9 * * 1-5'` |
| "every Monday" | `field: 'cronExpression', expression: '0 9 * * 1'` |
| "every 30 seconds" | `field: 'seconds', secondsInterval: 30` |
| "twice a day (9am and 5pm)" | Two intervals: `expression: '0 9 * * *'` + `expression: '0 17 * * *'` |
| "first of every month" | `field: 'cronExpression', expression: '0 0 1 * *'` |

**Note:** For simple intervals (every N minutes/hours), use the interval fields. For complex patterns (weekdays only, specific days, multiple times), use `cronExpression`.

### 2. EVENT-DRIVEN / WEBHOOK
**Signal words:** "when", "whenever", "on new", "on change", "if something happens", "receives a request", "API call", "incoming"
**Pattern:** Webhook/App Trigger → Process → Act
**Key nodes:** `n8n-nodes-base.webhook`, service-specific triggers (gmailTrigger, slackTrigger, githubTrigger, etc.)
**SDK pattern:** `.add(trigger).to(processNode).to(actionNode)`

### 3. BRANCHING (IF/ELSE)
**Signal words:** "if", "when [condition]", "otherwise", "depending on", "based on", "only if", "unless", "when X do A, when Y do B"
**Pattern:** Trigger → Check Condition → True Path / False Path
**Key nodes:** `n8n-nodes-base.if` (2 outputs), `n8n-nodes-base.switch` (N outputs)
**SDK pattern:** `.to(checkValid.onTrue(pathA).onFalse(pathB))`
**Important:** Each branch defines a COMPLETE processing path. Chain multiple steps INSIDE the branch using .to()

### 4. MULTI-WAY ROUTING (SWITCH)
**Signal words:** "route by", "categorize", "sort into", "different types", "priority levels", "multiple categories"
**Pattern:** Trigger → Switch on Field → Category A / Category B / Category C / ...
**Key nodes:** `n8n-nodes-base.switch`
**SDK pattern:** `.to(routeByType.onCase(0, chainA).onCase(1, chainB).onCase(2, chainC))`

### 5. PARALLEL EXECUTION
**Signal words:** "at the same time", "simultaneously", "in parallel", "both", "and also", "combine results from"
**Pattern:** Trigger → [Branch A + Branch B] → Merge → Continue
**Key nodes:** `n8n-nodes-base.merge` (modes: append, combine by position, combine by fields)
**SDK pattern:** Uses `.input(0)` and `.input(1)` on merge node
**Important:** Independent sources need `executeOnce: true` OR parallel branches + Merge to avoid item multiplication

### 6. BATCH PROCESSING / LOOP
**Signal words:** "for each", "process every", "loop through", "iterate", "one by one", "in batches", "paginate"
**Pattern:** Trigger → Fetch All → Split in Batches → Process Each → Loop Back → Done
**Key nodes:** `n8n-nodes-base.splitInBatches`
**SDK pattern:** `.to(sib.onDone(finalizeNode).onEachBatch(processNode.to(nextBatch(sib))))`

### 7. AI AGENT (only when user explicitly asks for an external LLM)
**Signal words:** "AI agent with my OpenAI key", "use GPT-4o", "use Claude API", "use Gemini", "autonomous agent with tools", "external LLM"
**Pattern:** Trigger → AI Agent (with LLM model + tools + optional memory)
**Key nodes:** `@n8n/n8n-nodes-langchain.agent`, LLM models, tool nodes
**SDK pattern:** Uses `languageModel()`, `tool()`, `memory()` as subnodes in agent config
**Important:** Every agent in a conversational workflow MUST have a memory subnode. Use `fromAi()` for AI-controlled tool parameters.
**DO NOT propose this pattern by default.** Use CITM (pattern 17/18a) for ALL reasoning tasks unless the user explicitly asks for an external LLM API. Real-time sub-second chat is the one legitimate use case — everything else belongs in CITM.

### 8. CHATBOT / CONVERSATIONAL (real-time chat only)
**Signal words:** "chat", "conversation", "talk to", "ask questions", "chatbot", "webchat", "messaging"
**Pattern:** Chat Trigger → AI Agent (with memory) → Response
**Key nodes:** `@n8n/n8n-nodes-langchain.chatTrigger`, `@n8n/n8n-nodes-langchain.agent`, `@n8n/n8n-nodes-langchain.memoryBufferWindow`
**SDK pattern:** Chat trigger with `loadPreviousSession` + agent with memory subnode
**Important:** When loadPreviousSession is "memory", the Agent MUST also have its own memory subnode. This is the one pattern where an external LLM API is justified by default — chat UX requires sub-second streaming that the CITM daemon's 15s poll can't match.

### 9. RAG (Retrieval Augmented Generation)
**Signal words:** "knowledge base", "answer from documents", "search documents", "RAG", "vector store", "embeddings", "ingest documents"
**Pattern:** [Ingest: Document → Split → Embed → Store] + [Query: Chat → Agent with Vector Store Retriever → Response]
**Key nodes:** Document loaders, text splitters, embeddings, vector stores, retriever, agent
**SDK pattern:** Two workflows or two branches — one for ingestion, one for querying

### 10. MULTI-TRIGGER / FAN-IN
**Signal words:** "either when", "or when", "from multiple sources", "any of these triggers"
**Pattern:** [Trigger A + Trigger B] → Shared Processing Chain
**Key nodes:** Multiple trigger nodes connecting to the same first processing node
**SDK pattern:** `.add(triggerA).to(sharedNode).add(triggerB).to(sharedNode)`
**Important:** Each trigger's execution runs in COMPLETE ISOLATION. Never duplicate chains for "isolation".

### 11. ERROR HANDLING
**Signal words:** "handle errors", "if it fails", "fallback", "retry", "error notification", "catch errors"
**Pattern:** Any node with `.onError()` connecting to a handler
**Key nodes:** `n8n-nodes-base.errorTrigger` (workflow-level), `.onError()` (node-level)
**SDK pattern:** `node.onError(errorHandler)` with `config: { onError: 'continueErrorOutput' }`
**Full implementation details:** See `references/error-handling-patterns.md` for 5 validated SDK patterns (retry backoff, dead letter queue, error alerts, circuit breaker, graceful degradation)

### 12. SUB-WORKFLOW / MODULAR
**Signal words:** "reusable", "call another workflow", "sub-workflow", "modular", "shared logic"
**Pattern:** Main Workflow → Execute Sub-workflow → Continue
**Key nodes:** `n8n-nodes-base.executeWorkflow`, `n8n-nodes-base.executeWorkflowTrigger`
**SDK pattern:** Regular node call to executeWorkflow with workflowId parameter

### 13. FORM-BASED
**Signal words:** "form", "user input", "fill out", "submit", "multi-step form", "wizard"
**Pattern:** Form Trigger → [Optional: Additional Form Pages] → Process → Respond
**Key nodes:** `n8n-nodes-base.formTrigger`, `n8n-nodes-base.form`
**SDK pattern:** Form trigger with form page nodes chained for multi-step

### 14. DATA TRANSFORMATION
**Signal words:** "transform", "map", "filter", "sort", "aggregate", "summarize", "convert", "restructure", "rename fields"
**Pattern:** Source → Transform → Destination
**Key nodes:** `n8n-nodes-base.set`, `n8n-nodes-base.filter`, `n8n-nodes-base.sort`, `n8n-nodes-base.aggregate`, `n8n-nodes-base.summarize`, `n8n-nodes-base.splitOut`, `n8n-nodes-base.removeDuplicates`, `n8n-nodes-base.code`

### 15. SCRAPING / RESEARCH
**Signal words:** "scrape", "crawl", "extract from website", "web research", "fetch page", "parse HTML"
**Pattern:** Trigger → HTTP Request → HTML Extract → Process → Store
**Key nodes:** `n8n-nodes-base.httpRequest`, `n8n-nodes-base.htmlExtract`, `n8n-nodes-base.code`
**Recommended:** Phantombuster for social media, Airtop for complex scraping, Jina AI for LLM-friendly extraction

### 16. TOOL WORKFLOW (for Claude Agent Mode)
**Signal words:** "agent tool", "tool workflow", "callable workflow", "webhook tool", "reusable tool", "Claude as agent"
**Pattern:** Webhook Trigger (POST, responseNode) → Do Work → Format JSON → Respond to Webhook
**Key nodes:** `n8n-nodes-base.webhook` (responseMode: responseNode), `n8n-nodes-base.respondToWebhook`, processing nodes
**Purpose:** Small single-purpose workflows that Claude calls via HTTP during agentic execution. Each tool does ONE thing (scrape, enrich, store, notify).
**Naming:** Workflow name starts with "Tool: " prefix. Webhook path: `tool-{name}`.
**Critical:** Must be published (activated) for the webhook to accept calls.
**Input/Output contract:** Input as JSON body `{ "param": "value" }`, output as `{ "success": true/false, "data": {...}, "error": "..." }`

### 17. CLAUDE-IN-THE-MIDDLE (Wait Node Pattern)
**Signal words:** "Claude analyzes in the middle", "pause for AI", "human-in-the-loop reasoning", "AI processing step"
**Pattern:** Trigger → Collect Data → Prepare → Wait (webhook, POST) → Use Claude Output → Act
**Key nodes:** `n8n-nodes-base.wait` (resume: webhook, httpMethod: POST)
**How it works:** Workflow runs until the Wait node, pauses with status "waiting". Claude reads the paused execution data via `get_execution`, analyzes it (free AI reasoning), then POSTs JSON to the resume URL (`$execution.resumeUrl`). Workflow resumes and the post-Wait nodes access Claude's data via `$json.body.*`.
**Pre-Wait data access:** `$("Node Before Wait").item.json.field`
**Claude's data access:** `$json.body.fieldName`
**Critical:** Wait node must use `httpMethod: 'POST'` and `resume: 'webhook'`. POST ensures Claude's JSON arrives in `$json.body`, not query params.
**Full implementation:** See `references/claude-in-the-middle.md` for complete batch processing architecture, operation-specific batch sizes, and sub-workflow SDK patterns.

### 18a. CLAUDE-IN-THE-MIDDLE — DEFAULT for every AI reasoning task
**Signal words:** "classify", "score", "generate", "analyze", "extract", "summarize", "translate", "moderate", "route", "personalize", "enrich", "decide", "rank" — basically any text-in/text-out reasoning operation
**Pattern:** Inline Wait node in the main workflow. Build Payload Code node outputs a field ending in `_instructions`, Wait node pauses, CITM runtime daemon spawns a fresh `claude` subprocess that reads the payload, follows the instructions, and POSTs the JSON result back to the signed resume URL. Next node parses.
**Key nodes:** `n8n-nodes-base.wait` (resume: webhook, POST), `n8n-nodes-base.code` (build payload + parse result)
**Runtime required:** `plugins/n8n-workflow-builder/runtime/install.py` — cross-platform background daemon that detects every paused Wait node across all workflows and spawns Claudes in parallel up to `max_concurrent_claudes`.
**Convention:** Upstream node output must contain a field whose key ends in `_instructions` (e.g. `classify_instructions`, `judge_instructions`). The runtime reads that field as Claude's task brief.
**When to use:** Default for EVERY reasoning task. Do NOT propose LLM API nodes unless the user explicitly asks for a specific external model or needs sub-second latency / image / audio / embedding capabilities.
**High-volume variant:** For 200+ items, split into batches via Execute Workflow sub-workflow. Each sub-execution pauses at its Wait node and is resolved in parallel by the runtime. See `references/claude-in-the-middle.md`.

**Full stateful pattern details:** See `references/stateful-patterns.md` for 7 complete patterns with SDK code examples (dedup, diff, persistence, approval, sync, audit, forms).

### 18. STATEFUL — Process Only New Items (Cross-Execution Dedup)
**Signal words:** "only new", "skip already processed", "don't process twice", "new items only", "since last run"
**Pattern:** Schedule → Fetch All → Remove Duplicates (seen in previous executions) → Process New Only
**Key nodes:** `n8n-nodes-base.removeDuplicates` (operation: removeItemsSeenInPreviousExecutions)
**How it works:** n8n internally remembers processed item keys across executions. No external DB needed.

### 19. STATEFUL — Detect Changes (Diff Old vs New)
**Signal words:** "what changed", "new vs old", "detect changes", "compare with previous", "sync"
**Pattern:** Schedule → Fetch Current → [Compare Datasets ← DataTable: Previous Snapshot] → Route: new/changed/deleted
**Key nodes:** `n8n-nodes-base.compareDatasets`, `n8n-nodes-base.dataTable`
**Compare Datasets outputs:** Output 0 = only in input 1 (new), Output 1 = only in input 2 (deleted), Output 2 = in both but different (changed)

### 20. STATEFUL — Human Approval (Wait for Decision)
**Signal words:** "approve", "manager needs to review", "human in the loop", "wait for confirmation", "sign off"
**Pattern:** Trigger → Process → Notify Approver → Wait for Response → Route: approved/rejected
**Key nodes:** `n8n-nodes-base.wait` (resume: form) or Slack/Gmail/Teams `sendAndWait` operation
**Services with sendAndWait:** Slack, Gmail, Microsoft Teams, Microsoft Outlook, Telegram, WhatsApp, Discord

### 21. STATEFUL — Persistent State (DataTable as Memory)
**Signal words:** "remember", "save for next run", "track status", "state machine", "running total", "accumulate"
**Pattern:** Any trigger → Read State from DataTable → Process → Write Updated State to DataTable
**Key nodes:** `n8n-nodes-base.dataTable` (upsert for state, rowExists for checking)
**Key operations:** `upsert` (create or update), `rowExists` (2-output routing node), `rowNotExists`

### 22. STATEFUL — Multi-Step Form Wizard
**Signal words:** "multi-step form", "wizard", "multiple pages", "step by step form", "questionnaire"
**Pattern:** Form Trigger (page 1) → Form (page 2) → Form (page 3) → Form (completion) → Process All Data
**Key nodes:** `n8n-nodes-base.formTrigger`, `n8n-nodes-base.form` (operation: page/completion)
**Note:** All form data from all pages is available in the final node as merged `$json`

## Complexity Classification

| Criterion | Simple | Moderate | Complex |
|-----------|--------|----------|---------|
| Node count | 2-4 | 5-8 | 9+ |
| Patterns combined | 1 | 2 | 3+ |
| Service categories | 1-2 | 2-3 | 4+ |
| Has AI/LLM nodes | No | Optional | Yes |
| Has branching/parallel | No | Maybe | Yes |
| Has sub-workflows | No | No | Maybe |

## Technique Category Mapping

Map user intent to `get_suggested_nodes` categories:

| User Intent | Categories |
|-------------|------------|
| Chat, assistant, Q&A | chatbot |
| Alert, notify, message | notification |
| Periodic, recurring, cron | scheduling |
| Transform, map, filter, merge | data_transformation |
| Store, save, database, sheets | data_persistence |
| Parse, extract, read file | data_extraction |
| PDF, invoice, document | document_processing |
| Form, survey, input | form_input |
| Generate text, image, content | content_generation |
| Classify, route, prioritize | triage |
| Scrape, research, web search | scraping_and_research |
