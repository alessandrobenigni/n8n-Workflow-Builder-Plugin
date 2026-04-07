# Claude-in-the-Middle: Complete Reference

When a workflow needs AI processing (classification, scoring, generation, extraction, etc.), users can choose **Claude-in-the-Middle** instead of an LLM API node. Claude does the reasoning for $0 — n8n handles the mechanics.

## When to Offer This Option

In Phase 3 (DESIGN), whenever the workflow blueprint includes ANY of these AI operations, offer the choice using `AskUserQuestion`:

- question: "This workflow needs AI to [operation]. How should it be powered?"
- header: "AI Engine"
- options:
  - label: "Claude-in-the-Middle (Free)", description: "$0 cost — Claude processes data when you run the workflow. Handles batches automatically."
  - label: "LLM API (needs API key)", description: "Costs per token — runs autonomously 24/7 without you present."

## Operations Claude CAN Replace

Every text-in/text-out AI operation:

| Operation | Typical Use Case | Batch Size |
|-----------|-----------------|------------|
| **Classification** | Sort emails by priority, categorize tickets, tag content | **50 items** |
| **Sentiment analysis** | Analyze feedback, reviews, social mentions | **50 items** |
| **Content moderation** | Check if content violates policies | **40 items** |
| **Translation** | Translate text between languages | **30 items** |
| **Lead scoring** | Score leads by ICP fit with reasoning | **25 items** |
| **Decision routing** | Route items by complex criteria | **30 items** |
| **Email personalization** | Write custom outreach per lead | **20 items** |
| **Information extraction** | Pull structured data from unstructured text | **15 items** |
| **Content generation** | Write articles, posts, descriptions | **15 items** |
| **Code generation** | Generate code, SQL, formulas | **10 items** |
| **Q&A with context** | Answer questions from provided documents | **10 items** |
| **Summarization** | Condense long text into summaries | **8 items** |
| **Reranking** | Reorder search results by relevance | **10 items** |
| **Document analysis** | Analyze full PDFs, contracts, reports | **3 items** |
| **Data enrichment** | Infer missing fields from available data | **25 items** |
| **Prompt optimization** | Improve/refine prompt text | **20 items** |

## Operations Claude CANNOT Replace

These need specialized models or infrastructure — always use the API node:

| Operation | Why | API Needed |
|-----------|-----|-----------|
| Image generation (DALL-E, Imagen) | Needs diffusion model | OpenAI / Google |
| Audio generation (TTS) | Needs speech synthesis | OpenAI |
| Audio transcription (Whisper) | Needs speech-to-text model | OpenAI |
| Video generation (Sora, Veo) | Needs video model | OpenAI / Google |
| Embeddings generation | Needs embedding model | OpenAI / Cohere / etc. |
| Vector store operations | Infrastructure, not reasoning | Pinecone / Qdrant / etc. |
| Web search | Needs search index | SerpAPI / Perplexity |
| OCR text extraction | Needs OCR model | Mistral / AWS Textract |

## Architecture: Parallel Agent Batch Processing

The recommended architecture spawns a **dedicated Claude agent per batch**. Each agent gets a fresh context window, focuses only on its batch, and agents run in parallel — 4x faster with higher quality than sequential processing.

```
┌─────────────────────────────────────────────────────────────────┐
│  CLAUDE (main conversation — coordinator)                       │
│                                                                 │
│  1. Trigger main workflow → n8n splits data into N batches      │
│  2. Each batch launches a sub-workflow that pauses at Wait      │
│  3. Claude reads all paused executions                          │
│  4. Spawns agents in parallel waves (4 at a time):              │
│                                                                 │
│     Wave 1: Agent 1 (batch 1) ─┐                               │
│             Agent 2 (batch 2) ─┤ parallel                      │
│             Agent 3 (batch 3) ─┤                               │
│             Agent 4 (batch 4) ─┘                               │
│                                                                 │
│     Wave 2: Agent 5 (batch 5) ─┐                               │
│             Agent 6 (batch 6) ─┤ parallel                      │
│             Agent 7 (batch 7) ─┤                               │
│             Agent 8 (batch 8) ─┘                               │
│                                                                 │
│  5. Each agent: read batch → process → POST results → done     │
│  6. Main Claude collects all results, reports summary           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  n8n (mechanical layer)                                         │
│                                                                 │
│  MAIN WORKFLOW:                                                 │
│  [Trigger] → [Fetch all items] → [Split into N batches]        │
│    → [For each batch: Execute Sub-workflow] → [Collect results] │
│                                                                 │
│  SUB-WORKFLOW (one execution per batch, all pause at Wait):     │
│  [Receive batch] → [Format] → [WAIT] → [Parse results] → [Return]
│                                  ↑                              │
│                          Agent POSTs here                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Parallel Agents Are Better

| | Sequential (one Claude) | Parallel Agents |
|---|---|---|
| **Speed** | 20 batches × 30s = 10 min | 20 batches / 4 parallel = 5 waves × 30s = **2.5 min** |
| **Quality** | Context accumulates — batch 15 has batches 1-14 in memory | Each agent has **fresh context** — no pollution |
| **Consistency** | Reasoning may drift across batches | Every agent gets the **exact same prompt** |
| **Failure isolation** | One bad batch stalls everything | Bad batch fails alone, others continue |

### Sub-workflow (Claude Batch Processor)

This workflow is deployed ONCE and called N times (once per batch). Each execution pauses independently at its Wait node.

```javascript
const receiveBatch = trigger({
  type: 'n8n-nodes-base.executeWorkflowTrigger',
  version: 1.1,
  config: { name: 'Receive Batch', position: [240, 300] },
  output: [{ items: [{ id: 1, text: 'item data' }] }]
});

const formatForClaude = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Format Batch for Claude',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const items = $input.all().map((item, i) => ({ index: i, ...item.json }));\nreturn [{ json: { batchSize: items.length, items: items, instruction: 'TASK_INSTRUCTION_HERE' } }];"
    },
    position: [540, 300]
  },
  output: [{ batchSize: 25, items: [...], instruction: '...' }]
});

const waitForClaude = node({
  type: 'n8n-nodes-base.wait',
  version: 1.1,
  config: {
    name: 'Wait for Claude Agent',
    parameters: {
      resume: 'webhook',
      httpMethod: 'POST',
      incomingAuthentication: 'none'
    },
    position: [840, 300]
  },
  output: [{ body: { processedItems: [...] } }]
});

const parseResults = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Parse Agent Results',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const results = $json.body.processedItems || [];\nreturn results.map(item => ({ json: item }));"
    },
    position: [1140, 300]
  },
  output: [{ id: 1, text: 'item data', classification: 'high', score: 85 }]
});

// Wire: receiveBatch → formatForClaude → waitForClaude → parseResults
```

### How Claude Orchestrates Parallel Agents

The main Claude conversation acts as coordinator:

**Step 1: Launch all batch sub-workflows**

Execute the main workflow which splits data and calls the sub-workflow per batch. Each sub-workflow execution pauses at its Wait node with a unique execution ID and resume URL.

**Step 2: Collect all paused execution IDs + resume URLs**

Read each execution's data to get the batch contents and resume URLs.

**Step 3: Spawn agents in parallel waves (max 4 per wave)**

Use the Agent tool with `run_in_background: true` to launch multiple agents simultaneously:

```
Agent tool call (all 4 in ONE message):

Agent 1: "Process batch 1. Read execution [id1] to get items.
  Classify each item as high/medium/low priority with reasoning.
  POST results to [resumeUrl1]."

Agent 2: "Process batch 2. Read execution [id2] to get items.
  Classify each item as high/medium/low priority with reasoning.
  POST results to [resumeUrl2]."

Agent 3: "Process batch 3. Read execution [id3]..."
Agent 4: "Process batch 4. Read execution [id4]..."
```

Each agent:
1. Calls `mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)` — reads its batch
2. Processes ALL items in the batch (fresh context, no pollution)
3. POSTs results to its resume URL:
```bash
curl -s -X POST "RESUME_URL" \
  -H "Content-Type: application/json" \
  -d '{ "processedItems": [...] }'
```
4. Reports completion back to main Claude

**Step 4: Wait for wave to complete, launch next wave**

When all 4 agents finish, launch the next 4. Repeat until all batches done.

**Step 5: Report final results**

```
Batch Processing Complete:
- 200 items processed across 8 batches
- 4 agents × 2 waves = 8 parallel executions
- Total time: ~60 seconds (vs ~4 minutes sequential)
- AI cost: $0.00
- Accuracy: Each agent had fresh context for optimal reasoning
```

### Agent Prompt Template

Each batch agent receives this prompt:

```
You are processing batch [N] of [TOTAL] for the "[OPERATION]" task.

INSTRUCTIONS:
[The specific task instruction — e.g., "Classify each support ticket by
priority (critical/high/medium/low) with a one-sentence reasoning."]

YOUR BATCH:
Read the data from execution [EXECUTION_ID] of workflow [WORKFLOW_ID]
using: mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)

The batch items are in the execution data at:
resultData.runData["Format Batch for Claude"][0].data.main[0][0].json

RESUME URL:
[RESUME_URL]

OUTPUT FORMAT:
POST a JSON body to the resume URL:
{
  "processedItems": [
    { ...original item fields, "result": "your classification/score/text", "reasoning": "brief explanation" },
    ...one entry per input item, same order
  ]
}

Process ALL items in the batch, then POST. Do not skip any items.
```

### Configuring Parallelism

| Dataset Size | Batch Size | Batches | Agents/Wave | Waves | Est. Time |
|-------------|-----------|---------|-------------|-------|-----------|
| 50 items | 25 | 2 | 2 | 1 | ~30s |
| 100 items | 25 | 4 | 4 | 1 | ~30s |
| 200 items | 25 | 8 | 4 | 2 | ~60s |
| 500 items | 25 | 20 | 4 | 5 | ~2.5min |
| 1000 items | 50 | 20 | 4 | 5 | ~2.5min |

Max 4 agents per wave (Claude Code's practical parallel limit). Each wave takes ~30 seconds for the agents to process + POST back.

## Batch Size Selection

The plugin automatically selects batch size based on the AI operation:

```python
BATCH_SIZES = {
    'classification': 50,
    'sentiment': 50,
    'moderation': 40,
    'translation': 30,
    'lead_scoring': 25,
    'decision_routing': 30,
    'email_personalization': 20,
    'information_extraction': 15,
    'content_generation': 15,
    'code_generation': 10,
    'qa_with_context': 10,
    'summarization': 8,
    'reranking': 10,
    'document_analysis': 3,
    'data_enrichment': 25,
    'default': 20
}
```

These are conservative — each batch uses ~200K tokens of Claude's 1M context, leaving massive room for reasoning.

## When NOT to Use Claude-in-the-Middle

- Workflow runs on a schedule without the user present (use LLM API)
- Workflow needs real-time response (<1 second, e.g., chatbot)
- Workflow processes images, audio, or video (use specialized API)
- Workflow generates embeddings for vector stores (use embedding API)
- User explicitly wants autonomous 24/7 operation
