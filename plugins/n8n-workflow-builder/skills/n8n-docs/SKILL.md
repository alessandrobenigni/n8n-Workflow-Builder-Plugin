---
name: n8n-docs
description: >-
  Auto-generate comprehensive markdown documentation for any n8n workflow.
  Analyzes nodes, data flow, credentials, triggers, and execution history
  to produce human-readable docs.
triggers:
  - n8n docs
  - n8n-docs
  - document workflow
  - generate docs
  - workflow documentation
  - explain workflow
  - describe workflow
  - what does this workflow do
  - document this
---

# n8n Workflow Documentation Generator

You auto-generate comprehensive documentation for any n8n workflow by analyzing its structure, nodes, connections, and execution history.

## Process

### Step 1: Identify the workflow

Accept workflow ID, name, or "this workflow" (if in context from a previous `/n8n` build).

```
mcp__n8n-mcp__search_workflows(query)
mcp__n8n-mcp__get_workflow_details(workflowId)
```

### Step 2: Analyze the workflow JSON

From `get_workflow_details`, extract:

1. **Metadata:** name, ID, active status, creation/update dates, description, tags
2. **Trigger:** type, configuration (schedule/cron expression, webhook path, trigger event)
3. **Nodes:** For each node — name, type, key parameters, credentials needed
4. **Connections:** Trace the connection graph to determine execution order and branching
5. **Error handling:** Which nodes have `.onError()` branches
6. **AI components:** Any AI Agent, LLM, memory, vector store subnodes

### Step 3: Enrich with local database

For each unique node type, look up the human-readable description:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/search.py --node <db_type>
```

### Step 4: Build the flow diagram

Using the connection graph, create an ASCII diagram following the format in `references/blueprint-format.md`. Show:
- Trigger at the left
- Linear flow with arrows
- Branches for If/Switch
- Parallel branches with merge points
- Error branches below main flow

### Step 5: Check execution history (optional)

If the workflow has been executed, get timing data:
```
mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)
```
Extract: last execution time, status, per-node timing, item counts.

### Step 6: Classify the workflow pattern

Map to the pattern taxonomy from `references/workflow-patterns.md`:
- Linear chain, branching, parallel, batch, AI agent, chatbot, RAG, etc.

### Step 7: Generate the documentation

Output this markdown structure:

```markdown
# [Workflow Name]

**ID:** [id] | **Status:** [Active/Draft] | **Pattern:** [type]
**Last Modified:** [date]

## Purpose
[1-3 sentence description of what the workflow does, inferred from nodes and data flow]

## Trigger
- **Type:** [Schedule/Webhook/Form/Chat/Manual/Event]
- **Configuration:** [cron expression, webhook path, event details]
- **Activation required:** [Yes for schedule/webhook triggers]

## Flow Diagram
```
[ASCII diagram]
```

## Nodes ([count] total)

| # | Node | Type | Purpose | Credentials |
|---|------|------|---------|-------------|
| 1 | [name] | [type] | [what it does] | [credential type or "none"] |
| 2 | ... | ... | ... | ... |

## Data Flow
1. [Trigger] fires → outputs: `{field1, field2}`
2. [Node 2] receives `$json.field1` → transforms → outputs: `{newField}`
3. [Node 3] receives `$json.newField` → ...

## Credentials Required
- **[Service]:** [credential type] — [what it's used for]
- **[Service]:** [credential type] — [what it's used for]

## Error Handling
[Describe error handling or note "No error handling configured"]

## Execution History
- Last run: [date] — [Status] ([duration])
- [Any notable patterns from recent executions]

## Notes
[Any important observations, limitations, or recommendations]
```

### Step 8: Offer to save

> "Documentation generated. Want me to:
> 1. Save it to a file (specify path)
> 2. Add it as a sticky note in the workflow
> 3. Just keep it in this conversation"
