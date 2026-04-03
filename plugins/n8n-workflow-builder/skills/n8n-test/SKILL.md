---
name: n8n-test
description: >-
  Test n8n workflows by executing them with sample data and comparing actual
  output against expected output. Supports multiple test cases, field-by-field
  comparison, and saving test suites for re-running.
triggers:
  - n8n test
  - n8n-test
  - test workflow
  - test my workflow
  - run tests
  - verify workflow
  - check workflow works
  - workflow tests
  - test suite
  - regression test
  - does it work
---

# n8n Workflow Testing

You test n8n workflows by executing them with defined inputs, then comparing actual outputs against expected results. You report PASS/FAIL with field-level diffs.

## Process

### Step 1: Identify the workflow

Accept workflow ID or name. Inspect it to understand the trigger type and nodes:
```
mcp__n8n-mcp__search_workflows(query)
mcp__n8n-mcp__get_workflow_details(workflowId)
```

Determine trigger type (manual, webhook, chat, form, schedule) — this determines how to provide test input.

### Step 2: Define test cases

Either the user provides test cases, or Claude generates sensible defaults based on the workflow structure.

**Test case format:**
```json
{
  "name": "Happy path - valid input",
  "input": {
    "type": "webhook",
    "webhookData": { "body": { "email": "test@example.com", "name": "Test User" } }
  },
  "expected": {
    "status": "success",
    "nodeChecks": {
      "Final Output": {
        "status": "success",
        "outputContains": { "processed": true }
      }
    }
  }
}
```

**Input types by trigger:**
- **Manual/Schedule:** `null` (no input needed, `executionMode: "manual"`)
- **Webhook:** `{ "type": "webhook", "webhookData": { "body": {...}, "method": "POST" } }`
- **Chat:** `{ "type": "chat", "chatInput": "test message" }`
- **Form:** `{ "type": "form", "formData": { "field1": "value1" } }`

**Expected output checks:**
- `status`: "success" or "error" — overall execution status
- `nodeChecks`: per-node assertions
  - `status`: "success" or "error" — did this node succeed?
  - `outputContains`: partial match — the actual output must contain these fields/values
  - `outputEquals`: exact match — the actual output must exactly match
  - `outputMatches`: regex — field values must match the pattern

### Step 3: Generate default test cases

If the user says "just test it" without specifying cases, auto-generate:

1. **Happy path test:** Use sensible defaults for the trigger type. For webhooks, construct a minimal valid payload based on what the first processing node expects.

2. **Empty input test:** Send minimal/empty data to see if error handling works.

3. **For scheduled workflows:** Execute manually and check that all nodes complete successfully.

> "I'll generate 2 test cases:
> 1. **Happy path** — Valid input with sample data
> 2. **Empty input** — Minimal data to test error handling
>
> Want to customize these, or should I run them?"

### Step 4: Execute each test case

For each test case:

```
mcp__n8n-mcp__execute_workflow(workflowId, inputs, executionMode: "manual")
```

Then get full results:
```
mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)
```

### Step 5: Compare actual vs expected

For each test case, check:

1. **Overall status:** Does `execution.status` match `expected.status`?
2. **Per-node status:** For each node in `expected.nodeChecks`, does the actual node execution status match?
3. **Output field checks:**
   - `outputContains`: For each key/value in expected, check if actual output has the same key with the same value (deep partial match)
   - `outputEquals`: Exact deep equality check
   - `outputMatches`: Regex test on string fields

### Step 6: Report results

```
TEST RESULTS: [Workflow Name] ([id])
Run at: [timestamp]

[PASS] Test 1: Happy path - valid input
  - Fetch Data: OK (3 items, 1.2s)
  - Transform: OK (3 items, 0.1s)
  - Final Output: OK
    - processed: true (expected: true) ✓
    - count: 3 (expected: > 0) ✓

[FAIL] Test 2: Empty input
  - Fetch Data: OK (0 items, 0.8s)
  - Transform: ERROR — Expected: success, Got: error
    DIFF: Node errored with "Cannot read property 'email' of undefined"
    SUGGESTION: Add null check or error handling in Transform node

Summary: 1/2 passed | 1 failed
```

### Step 7: Offer to save test suite

> "Want me to save these test cases for re-running later? They'll be stored locally and you can run `/n8n-test` again anytime."

Save to `${CLAUDE_PLUGIN_ROOT}/data/tests/<workflowId>.json`:
```json
{
  "workflowId": "abc123",
  "workflowName": "Morning Lead Pipeline",
  "testCases": [ ... ],
  "lastRun": "2026-04-03T10:00:00Z",
  "lastResult": { "passed": 1, "failed": 1, "total": 2 }
}
```

Use the test-runner utility:
```bash
# Save test suite
python3 ${CLAUDE_PLUGIN_ROOT}/data/test-runner.py --save <workflowId> '<test_json>'

# Load saved tests
python3 ${CLAUDE_PLUGIN_ROOT}/data/test-runner.py --load <workflowId>

# List all test suites
python3 ${CLAUDE_PLUGIN_ROOT}/data/test-runner.py --list

# Compare actual vs expected
python3 ${CLAUDE_PLUGIN_ROOT}/data/test-runner.py --compare '<actual_json>' '<expected_json>'
```

### Step 8: Offer to fix failures

For each FAIL, analyze the root cause and offer a fix:
> "Test 2 failed because the Transform node doesn't handle empty input. Want me to add a null check? I'll use `/n8n` to update the workflow."

### Re-running saved tests

When user says "run tests again" or "re-run tests":
1. Load saved test cases: `test-runner.py --load <workflowId>`
2. Execute each test case
3. Compare and report
4. Update the saved lastRun and lastResult
