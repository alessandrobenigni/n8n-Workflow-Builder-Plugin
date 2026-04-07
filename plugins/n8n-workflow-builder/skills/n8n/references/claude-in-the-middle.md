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

## Architecture: Batch Processing with Sub-Workflows

Claude can't process items one-at-a-time with 100 Wait/Resume cycles. Instead, use a **batch sub-workflow pattern**:

```
MAIN WORKFLOW:
[Trigger] → [Fetch items] → [Split into batches] → [Loop]
                                                      ↓
                                              [Execute Sub-workflow]
                                              (pass batch as input)
                                                      ↓
                                              [Collect batch results]
                                                      ↓
                                              [Next batch or Done]
                                                      ↓
[Done] → [Merge all results] → [Store/Notify]

SUB-WORKFLOW (Claude Processor):
[Execute Workflow Trigger] → [Format batch for Claude] → [WAIT node (POST)]
                                                              ↑
                                                         Claude reads batch,
                                                         processes all items,
                                                         POSTs results back
                                                              ↓
[WAIT resumes] → [Parse Claude results] → [Return to main workflow]
```

### Main workflow SDK pattern:

```javascript
const fetchItems = node({ /* fetch all data */ });

const batchLoop = splitInBatches({
  version: 3,
  config: {
    name: 'Process in Batches',
    parameters: { batchSize: 25 },  // ← Set based on operation type from table above
    position: [...]
  }
});

const callClaudeProcessor = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.3,
  config: {
    name: 'Send Batch to Claude',
    parameters: {
      operation: 'call_workflow',
      workflowId: 'CLAUDE_PROCESSOR_WORKFLOW_ID'
    },
    position: [...]
  },
  output: [{ processedItems: [...] }]
});

// Wire: trigger → fetchItems → batchLoop
//   .onDone(mergeResults)
//   .onEachBatch(callClaudeProcessor.to(nextBatch(batchLoop)))
```

### Sub-workflow (Claude Processor) SDK pattern:

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
    name: 'Wait for Claude Analysis',
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
    name: 'Parse Claude Results',
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

### How Claude Processes the Batch

When the sub-workflow pauses at the Wait node, Claude:

1. Calls `mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)` to read the batch
2. Sees the items array + instruction
3. Processes ALL items in one pass (e.g., classifies all 25 leads)
4. POSTs results back to the resume URL:

```bash
curl -s -X POST "RESUME_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "processedItems": [
      { "id": 1, "text": "...", "classification": "high", "score": 85, "reasoning": "..." },
      { "id": 2, "text": "...", "classification": "low", "score": 30, "reasoning": "..." },
      ...
    ]
  }'
```

5. Sub-workflow resumes, returns results to main workflow
6. Main workflow moves to next batch

### Claude's Processing Loop (what Claude actually does)

```
for each batch:
  1. get_execution → read items + instruction
  2. Analyze all items in the batch
  3. For each item: apply the instruction (classify/score/generate/etc.)
  4. POST all results back to resume URL
  5. Report progress: "Batch 3/20 complete (75 items processed)"
```

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
