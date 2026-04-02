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

### 7. AI AGENT
**Signal words:** "AI agent", "assistant", "intelligent", "can use tools", "decide what to do", "autonomous", "plan and execute"
**Pattern:** Trigger → AI Agent (with LLM model + tools + optional memory)
**Key nodes:** `@n8n/n8n-nodes-langchain.agent`, LLM models, tool nodes
**SDK pattern:** Uses `languageModel()`, `tool()`, `memory()` as subnodes in agent config
**Important:** Every agent in a conversational workflow MUST have a memory subnode. Use `fromAi()` for AI-controlled tool parameters.

### 8. CHATBOT / CONVERSATIONAL
**Signal words:** "chat", "conversation", "talk to", "ask questions", "chatbot", "webchat", "messaging"
**Pattern:** Chat Trigger → AI Agent (with memory) → Response
**Key nodes:** `@n8n/n8n-nodes-langchain.chatTrigger`, `@n8n/n8n-nodes-langchain.agent`, `@n8n/n8n-nodes-langchain.memoryBufferWindow`
**SDK pattern:** Chat trigger with `loadPreviousSession` + agent with memory subnode
**Important:** When loadPreviousSession is "memory", the Agent MUST also have its own memory subnode

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
