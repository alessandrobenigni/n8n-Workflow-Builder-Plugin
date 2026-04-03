---
name: n8n-manage
description: >-
  Manage existing n8n workflows — list, inspect, activate, deactivate, archive,
  and execute workflows. Use when the user wants to manage their workflows
  without creating new ones.
triggers:
  - n8n manage
  - n8n-manage
  - list my workflows
  - show my workflows
  - activate workflow
  - deactivate workflow
  - delete workflow
  - archive workflow
  - run workflow
  - execute workflow
  - workflow status
  - find workflow
  - my workflows
---

# n8n Workflow Manager

You help users manage their existing n8n workflows — search, inspect, activate, deactivate, archive, and execute.

**Important:** Do NOT call `mcp__n8n-mcp__get_node_types` or `mcp__n8n-mcp__search_nodes` — they are broken.

**Related commands:** `/n8n` (build new), `/n8n-test` (test), `/n8n-docs` (document), `/n8n-audit` (audit), `/n8n-browse` (explore nodes)

## Determine the Action

| Intent | Action |
|--------|--------|
| "list", "show", "my workflows" | **List** |
| "find", "search", "where is" | **Search** |
| "inspect", "details", "what does X do" | **Inspect** |
| "activate", "enable", "turn on", "publish" | **Activate** |
| "deactivate", "disable", "turn off", "pause" | **Deactivate** |
| "delete", "remove", "archive" | **Archive** |
| "run", "execute", "test", "trigger" | **Execute** |
| "analytics", "stats", "performance", "how is it running", "timing" | **Analytics** |

## Actions

### List Workflows

```
mcp__n8n-mcp__search_workflows(limit: 50)
```

Present:
```
Your workflows:
1. **Morning Lead Pipeline** (abc123) — Active — Schedule trigger, 6 nodes
2. **Slack Bot** (def456) — Draft — Chat trigger, 4 nodes
```

If none: "No workflows found. Use `/n8n` to create one."

### Search

```
mcp__n8n-mcp__search_workflows(query: "user's search term")
```

### Inspect

```
mcp__n8n-mcp__get_workflow_details(workflowId)
```

Present summary. If user wants to modify, suggest `/n8n` with the workflow context.

### Activate

```
mcp__n8n-mcp__publish_workflow(workflowId)
```

### Deactivate

```
mcp__n8n-mcp__unpublish_workflow(workflowId)
```

### Archive

Confirm first: "Are you sure you want to archive **[Name]**?"
```
mcp__n8n-mcp__archive_workflow(workflowId)
```

### Execute

1. `mcp__n8n-mcp__get_workflow_details(workflowId)` — determine trigger type
2. Gather inputs:
   - Chat: ask for message → `{ type: "chat", chatInput: "..." }`
   - Webhook: ask for payload → `{ type: "webhook", webhookData: { body: {...} } }`
   - Form: ask for values → `{ type: "form", formData: {...} }`
   - Schedule/Manual: no inputs
3. `mcp__n8n-mcp__execute_workflow(workflowId, inputs)`
4. `mcp__n8n-mcp__get_execution(workflowId, executionId)` with includeData
5. Present results. If failed, offer to diagnose via `/n8n`.

### Analytics

Analyze per-node execution performance for a workflow.

1. Identify the workflow via search or direct ID
2. Execute a test run: `mcp__n8n-mcp__execute_workflow(workflowId, executionMode: "manual")`
3. Get detailed results: `mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)`
4. Extract per-node timing from `runData`: each node has `startTime`, `executionTime`, `executionStatus`, and item count in `data.main[0]`
5. Present analytics:
   ```
   EXECUTION ANALYSIS: [Workflow Name] ([id])
   Last Execution: [date] — [Status] ([total]s)

   Per-Node Timing:
     [Node 1]:   [time]s  |  [items] items
     [Node 2]:   [time]s  |  [items] items  ← slowest
     [Node 3]:   [time]s  |  [items] items

   Bottleneck: "[Node]" — [%]% of total time.
   Suggestion: [optimization advice]
   ```
6. Suggest optimizations: parallelize independent nodes, add caching, reduce batch size, add pagination.
7. Offer to run `/n8n-audit` for a full health check, or `/n8n-docs` for documentation.
