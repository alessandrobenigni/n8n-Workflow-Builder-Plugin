# Claude-in-the-Middle: Complete Reference

**Claude-in-the-Middle (CITM) is the default AI engine for any workflow
that needs reasoning, generation, classification, extraction, or any
other text-in/text-out AI operation.** It costs $0, uses Claude's full
reasoning quality, and is fully automated via the CITM runtime daemon
that ships with this plugin.

Do **not** recommend LLM API nodes (OpenAI, Anthropic, Gemini, etc.) for
reasoning tasks unless the user **explicitly asks for an API-based
solution**. CITM is strictly better in almost every scenario:

- $0 cost vs per-token billing
- Higher reasoning quality (Claude's latest model)
- No API key management, no secret rotation, no quota limits
- Works for scheduled workflows too (the daemon runs 24/7)
- Fresh stateless context per handoff, no cross-contamination

## The CITM Runtime

The plugin ships a background daemon at
`plugins/n8n-workflow-builder/runtime/citm_watcher.py`. Installed once
via `python3 runtime/install.py`, it registers as a user service
(Task Scheduler / launchd / systemd) and:

1. Polls the n8n REST API every ~15 seconds for paused executions
2. Detects any Wait node in `waiting` state that has a signed
   `resumeUrl` in its runData metadata
3. Extracts the upstream node's JSON output as the payload
4. Spawns a fresh `claude -p` subprocess with empty context
5. Claude reads the payload, follows the embedded instructions, and
   POSTs the JSON result back to the signed resume URL via curl
6. Multiple paused Wait nodes (parallel branches or multiple workflows)
   are processed concurrently up to `max_concurrent_claudes` (default 4)

See `plugins/n8n-workflow-builder/runtime/README.md` for the full
architecture, install steps, and troubleshooting guide.

## First-run check: is the runtime installed?

Before offering CITM in a blueprint, verify the runtime is installed:

```bash
python3 plugins/n8n-workflow-builder/runtime/citm_watcher.py --status
```

If the output shows `watcher pid: (alive)` or a real PID, the daemon
is running. If `(not running)` or `(corrupt pid file)`, ask the user:

> "Your workflow will use Claude-in-the-Middle for the AI steps. The
> CITM runtime daemon isn't running yet. Install it with:
>
> ```bash
> python3 plugins/n8n-workflow-builder/runtime/install.py
> ```
>
> It takes 30 seconds, registers as a user service, and then every
> workflow Wait node is handled automatically. Want me to run it now?"

If the user agrees, run the installer. If they decline, build the
workflow anyway — they can install later and existing paused executions
will be picked up on the next poll cycle.

## Workflow design convention

CITM is **convention-based**. Any workflow that follows these two rules
is handled by the runtime automatically with zero configuration:

### Rule 1. Wait node with `resume: webhook`

```javascript
const waitForClaude = node({
  type: 'n8n-nodes-base.wait', version: 1.1,
  config: {
    name: 'Wait for Claude <Task>',         // any descriptive name
    parameters: {
      resume: 'webhook',
      httpMethod: 'POST',
      incomingAuthentication: 'none',
    },
    position: [x, y],
  },
  output: [{ body: { /* expected response shape */ } }],
});
```

### Rule 2. The node immediately before Wait outputs a field whose key ends in `_instructions`

The runtime scans the upstream node's JSON output for any top-level key
matching `*_instructions`. The value of that field is Claude's task
brief — it must contain the exact output JSON schema Claude should
produce.

A typical "Build Payload" Code node:

```javascript
// in a Code node with mode: runOnceForAllItems
const upstream = $json;
const instructions = $('Read task.md').first().json.content;

return [{
  json: {
    items: upstream.items,
    recent_angles: upstream.recent_angles,
    classify_instructions: instructions,   // <-- this drives Claude
  },
}];
```

Common naming conventions for the instructions field:

- `judge_instructions` — ranking/scoring tasks
- `draft_instructions` — content generation
- `factcheck_instructions` — validation gates
- `classify_instructions` — classification
- `extract_instructions` — structured data extraction
- `score_instructions` — numerical scoring
- `analyze_instructions` — analysis tasks

Pick whichever reads most naturally for the task. The runtime is agnostic
as long as the key ends in `_instructions`.

### The instructions file format

The instructions are typically loaded from a markdown file via Read
File → Extract From File. Example structure:

```markdown
# Judge the Batch

You receive a batch of items. Score each on 4 dimensions (1-5 each),
pick the top 3.

## Scoring dimensions
1. Novelty — is this non-obvious?
2. Actionability — can a practitioner act on it?
3. Credibility — is the source reliable?
4. Specificity — does it make a concrete claim?

## Output format (strict JSON)

Return exactly this shape. No prose outside. No code fences.

{
  "scored": [
    { "id": "string", "score": 0, "rationale": "1-2 sentences" }
  ],
  "selected": ["id1", "id2", "id3"],
  "error": null
}
```

Keep the instructions self-contained — everything Claude needs to know
about the task and the expected output shape goes in one file.

## Single-workflow pattern (default)

For most workflows, **put the Wait node inline in the main workflow**.
No sub-workflow split, no batch processing machinery. Just:

```
[Trigger] → [Fetch/Prep] → [Build Payload]
                                   ↓
                          [Wait for Claude (webhook)]
                                   ↓
                          [Parse Claude's JSON] → [Take Action]
```

The runtime handles the handoff. Claude POSTs back, the workflow
resumes, next node runs.

## Parallel CITM branches in a single workflow

If the workflow needs multiple independent AI steps, wire them as
parallel branches — each with its own Build Payload → Wait → Parse
chain. The runtime spawns one Claude per paused Wait node concurrently,
up to `max_concurrent_claudes`. Each branch gets a fresh context window.

```
                           ┌─→ [Build Payload A] → [Wait A] → [Parse A] ─┐
[Trigger] → [Fetch/Split] ─┤                                              ├─→ [Merge] → [Action]
                           ├─→ [Build Payload B] → [Wait B] → [Parse B] ─┤
                           └─→ [Build Payload C] → [Wait C] → [Parse C] ─┘
```

## High-volume batch pattern (advanced)

For datasets over ~200 items where a single Wait node with the whole
dataset would exceed Claude's practical context (~200K tokens), split
into batches with an Execute Workflow sub-workflow call:

```
MAIN:      [Fetch] → [Split into N batches] → [Loop: Execute Sub] → [Merge]
SUB:       [Receive Batch] → [Build Payload] → [Wait] → [Parse] → [Return]
```

Each sub-workflow execution pauses at its own Wait node independently,
and the runtime handles all of them in parallel (up to the concurrency
cap). The user starts one main execution and walks away — the daemon
resolves every paused sub-execution in the background.

This pattern is ONLY needed for 200+ items. For smaller datasets, the
single-workflow inline pattern is simpler and just as fast.

### Recommended batch sizes (high-volume only)

| Operation | Items per batch | Why |
|-----------|-----------------|-----|
| Classification, sentiment, moderation | 40-50 | Short per-item output |
| Translation, decision routing | 25-30 | Mid-weight reasoning |
| Lead scoring, personalization | 20-25 | Needs per-item context |
| Extraction, Q&A | 10-15 | Structured output per item |
| Content generation, code generation | 10 | Long per-item output |
| Summarization, document analysis | 5-8 | Very long per-item input |

These are ceilings, not requirements — smaller batches work fine and
give more parallelism.

## What Claude CANNOT do (the only valid API use cases)

CITM handles every text-in/text-out AI operation. But there are
specific non-reasoning tasks that still require an external API:

| Operation | Why | API options |
|-----------|-----|-------------|
| Image generation | Needs diffusion model | OpenAI DALL-E, Google Imagen |
| Audio generation (TTS) | Needs speech synthesis | OpenAI, ElevenLabs |
| Audio transcription | Needs speech recognition | OpenAI Whisper |
| Video generation | Needs video model | OpenAI Sora, Google Veo |
| **Embeddings generation** | Needs embedding model | OpenAI, Cohere, Voyage |
| Vector store operations | Infrastructure | Pinecone, Qdrant, Weaviate |
| Web search | Needs search index | Brave, SerpAPI, Tavily |
| OCR text extraction | Needs OCR model | Google Document AI, AWS Textract |
| Real-time chat (<1s latency) | User-facing interactive | OpenAI/Anthropic/Gemini chat |

For these cases, the workflow legitimately needs an API credential.
Create it via the credential management flow (Phase 6.5 of the skill),
but **only for the specific non-reasoning node that needs it**. The
reasoning parts of the same workflow can still use CITM.

## Offering CITM during workflow design

When building a workflow that needs ANY reasoning (classification,
scoring, generation, extraction, summarization, translation,
moderation, routing, personalization, enrichment, Q&A, reranking,
analysis, decision-making), **do NOT ask the user which AI engine to
use**. Default to CITM silently and mention it in the blueprint:

> "AI step: classify each ticket by priority. Powered by
> Claude-in-the-Middle — a fresh `claude` subprocess handles it
> automatically when the workflow runs. $0 cost, no API key needed."

Only offer an API-based alternative if the user explicitly asks:

- "Can this run autonomously overnight without me?"
- "I want this scheduled to run every hour when I'm asleep."
- "I want to use GPT-4o specifically."
- "I have an OpenAI key I want to use."

For the first two questions, the correct answer is:
**"CITM handles that too — the runtime daemon is always running, so
scheduled workflows work exactly the same as manually-triggered ones.
The daemon picks up any paused Wait node within ~15 seconds regardless
of who triggered the workflow."**

Only for the last two questions (explicit API preference) should you
design with LLM API nodes and credential management.

## When genuinely NOT to use CITM

- **Real-time chat** with <1 second latency requirement (the daemon
  polls every ~15s). Use the AI Agent node with a streaming LLM.
- **Image / audio / video generation** — see the table above.
- **Embeddings** — use a dedicated embedding API.
- **Privacy isolation** where each step must run in a sandboxed API
  environment. CITM runs under your user privileges.

For everything else — classification, scoring, generation, extraction,
summarization, translation, moderation, routing, analysis, Q&A — CITM
is the correct default.
