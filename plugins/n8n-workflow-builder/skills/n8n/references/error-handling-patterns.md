# Error Handling Patterns for n8n Workflows

Use these validated SDK patterns when building workflows with external API calls, database writes, or any operation that can fail. Each pattern is copy-paste ready.

## When to Suggest Error Handling

**Always suggest** when the workflow contains:
- HTTP Request nodes (APIs go down)
- Database write nodes (connections drop)
- External service nodes with credentials (auth can expire)
- Batch processing (partial failures happen)
- Webhook-triggered workflows (input can be malformed)

**Ask the user:** "This workflow calls external APIs. Want me to add error handling? Options:"
1. Retry with backoff (auto-retry failed API calls)
2. Error alerts (Slack/email notification on failure)
3. Skip and continue (graceful degradation)
4. Dead letter queue (save failed items for later)
5. Circuit breaker (stop after repeated failures)

## Pattern 1: Retry with Exponential Backoff

**Use when:** API calls may fail due to rate limits, temporary outages, or network issues.

The HTTP Request node has built-in retry support:

```javascript
const apiCall = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Call External API',
    parameters: {
      method: 'GET',
      url: 'https://api.example.com/data',
      options: {
        timeout: 15000,
        retry: {
          enabled: true,
          maxRetries: 3,
          retryInterval: 1000,      // 1 second initial delay
          retryIntervalBackoff: true // exponential: 1s, 2s, 4s
        }
      }
    },
    position: [...]
  },
  output: [{ data: 'result' }]
});
```

**Key:** `retry.enabled: true` + `retryIntervalBackoff: true` = automatic exponential backoff.

## Pattern 2: Dead Letter Queue (Store Failed Items)

**Use when:** You can't lose data. Failed items must be saved for manual review or reprocessing.

```javascript
const riskyApiCall = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Call Risky API',
    parameters: { method: 'POST', url: 'https://api.example.com/process' },
    onError: 'continueErrorOutput',
    position: [840, 300]
  },
  output: [{ result: 'ok' }]
});

const saveFailedItem = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Save to Dead Letter Queue',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const item = $input.first().json;\nreturn [{ json: {\n  originalData: item,\n  error: item.error?.message || 'Unknown error',\n  failedAt: new Date().toISOString(),\n  workflowId: $execution.id,\n  nodeName: 'Call Risky API'\n} }];"
    },
    position: [1140, 500]
  },
  output: [{ originalData: {}, error: 'API timeout', failedAt: '2026-01-01T00:00:00Z', workflowId: '123', nodeName: 'Call Risky API' }]
});

// Wire: riskyApiCall.onError(saveFailedItem) in the workflow composition
// saveFailedItem can chain to a DataTable insert, Google Sheet append, or any storage
```

## Pattern 3: Error Notification (Slack/Email Alert)

**Use when:** Ops team needs to know immediately when something fails.

```javascript
const riskyNode = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Critical API Call',
    parameters: { method: 'POST', url: 'https://api.example.com/critical' },
    onError: 'continueErrorOutput',
    position: [840, 300]
  },
  output: [{ result: 'ok' }]
});

const alertOnError = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Format Error Alert',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const item = $input.first().json;\nconst errorMsg = item.error?.message || JSON.stringify(item);\nreturn [{ json: {\n  text: '\\u26a0\\ufe0f Workflow Error\\n\\nWorkflow: ' + $workflow.name + '\\nNode: Critical API Call\\nError: ' + errorMsg + '\\nTime: ' + new Date().toISOString() + '\\nExecution: ' + $execution.id\n} }];"
    },
    position: [1140, 500]
  },
  output: [{ text: 'Workflow Error...' }]
});

// Chain alertOnError to a Slack node (resource=message, operation=post)
// or Gmail node (resource=message, operation=send)
```

**Workflow-level catch-all:** Use Error Trigger for a separate workflow that catches ALL failures:

```javascript
const errorTrigger = trigger({
  type: 'n8n-nodes-base.errorTrigger',
  version: 1,
  config: { name: 'Catch All Errors', position: [240, 300] },
  output: [{ execution: { id: '123', error: { message: 'Something failed' } } }]
});
// Chain to a notification node — this workflow runs whenever ANY other workflow fails
```

## Pattern 4: Circuit Breaker (Stop After N Failures)

**Use when:** You don't want to keep hammering a dead API. Stop after repeated failures.

```javascript
const checkHealth = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Check Circuit Breaker',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "// Read failure count from execution data or static storage\n// For simplicity, use a DataTable to track state\nconst MAX_FAILURES = 3;\nconst currentFailures = $input.first().json.consecutiveFailures || 0;\nif (currentFailures >= MAX_FAILURES) {\n  return [{ json: { circuitOpen: true, message: 'Circuit breaker tripped after ' + MAX_FAILURES + ' failures. Manual intervention required.' } }];\n}\nreturn [{ json: { circuitOpen: false, consecutiveFailures: currentFailures } }];"
    },
    position: [540, 300]
  },
  output: [{ circuitOpen: false, consecutiveFailures: 0 }]
});

// Follow with an If node:
// circuitOpen === true → alert + stop
// circuitOpen === false → proceed with API call
```

## Pattern 5: Graceful Degradation (Skip Failed Step, Continue)

**Use when:** One step failing shouldn't kill the entire workflow. Use defaults instead.

```javascript
const enrichmentCall = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Enrich with External API',
    parameters: { method: 'GET', url: expr('https://api.enrichment.com/lookup?email={{ $json.email }}') },
    onError: 'continueErrorOutput',
    position: [840, 300]
  },
  output: [{ company: 'Acme Inc', industry: 'Tech' }]
});

const provideFallbackData = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Use Fallback Defaults',
    parameters: {
      mode: 'manual',
      assignments: {
        assignments: [
          { id: 'c', name: 'company', type: 'string', value: 'Unknown' },
          { id: 'i', name: 'industry', type: 'string', value: 'Unknown' },
          { id: 'e', name: 'enrichmentFailed', type: 'boolean', value: 'true' }
        ]
      }
    },
    position: [1140, 500]
  },
  output: [{ company: 'Unknown', industry: 'Unknown', enrichmentFailed: true }]
});

const mergeBackToMainFlow = merge({
  version: 3.2,
  config: {
    name: 'Continue Either Way',
    parameters: { mode: 'append' },
    position: [1440, 400]
  }
});

// Wire:
// enrichmentCall (success) → mergeBackToMainFlow.input(0)
// enrichmentCall.onError(provideFallbackData) → mergeBackToMainFlow.input(1)
// mergeBackToMainFlow → next processing step
```
