# Stateful Workflow Patterns

Most workflows are stateless — they process data and forget. But many real-world automations need **memory**: track what's been processed, compare with previous runs, persist results, or wait for human approval. These patterns use n8n's built-in stateful capabilities.

## When to Suggest These Patterns

**Always ask** when the user's workflow involves:
- Recurring/scheduled tasks processing changing data ("new items", "changes since last run")
- Any phrase suggesting comparison: "new", "changed", "updated", "different", "same as before"
- Deduplication needs: "don't process twice", "skip already seen", "only new ones"
- Human approval: "approve", "review", "sign off", "manager needs to confirm"
- Persistent storage: "remember", "save for later", "track", "log", "history"
- Multi-step processes spanning time: "first do X, then later do Y"

---

## Pattern 1: Process Only New Items (Cross-Execution Deduplication)

**Use when:** A scheduled workflow fetches data from an API and should only process items it hasn't seen before.

**Key node:** `n8n-nodes-base.removeDuplicates` with operation `removeItemsSeenInPreviousExecutions`

```javascript
const dedup = node({
  type: 'n8n-nodes-base.removeDuplicates',
  version: 2,
  config: {
    name: 'Only New Items',
    parameters: {
      operation: 'removeItemsSeenInPreviousExecutions',
      logic: 'removeItemsWithAlreadySeenKeyValues',
      dedupeValue: expr('{{ $json.id }}'),
      options: { scope: 'workflow' }
    },
    position: [...]
  },
  output: [{ id: 'new-123', data: 'only new items pass through' }]
});
```

**How it works:** n8n internally stores the key values from each execution. On the next run, items with already-seen keys are filtered out. No external database needed.

**Example workflow:**
```
[Schedule: Every 15 min] → [Fetch API Data] → [Only New Items] → [Process] → [Notify]
```

**SDK config options:**
- `logic: 'removeItemsWithAlreadySeenKeyValues'` — Filter by unique ID field
- `logic: 'removeItemsUpToStoredIncrementalKey'` — Filter by incrementing number (e.g., database auto-increment ID)
- `logic: 'removeItemsUpToStoredDate'` — Filter by date field (process items newer than last processed)
- `options.scope: 'workflow'` — Dedup scope is per-workflow (default)
- `options.historySize: 10000` — How many keys to remember (default varies)

---

## Pattern 2: Detect Changes (Compare Old vs New Data)

**Use when:** You need to know what changed — new items, updated items, or deleted items since the last run.

**Key nodes:** `n8n-nodes-base.dataTable` (store previous snapshot) + `n8n-nodes-base.compareDatasets` (diff)

```
[Schedule] → [Fetch Current Data] ──────────────────→ [Compare Datasets] → [Route Changes]
                                                            ↑                    │
              [DataTable: Get Previous Snapshot] ──────────┘                    ├── New items → [Process New]
                                                                                ├── Changed items → [Process Changed]
                                                                                └── Deleted items → [Process Deleted]
              [DataTable: Save Current as New Snapshot] ←── [After processing]
```

**Compare Datasets node:**
```javascript
const comparator = node({
  type: 'n8n-nodes-base.compareDatasets',
  version: 2.3,
  config: {
    name: 'Find Changes',
    parameters: {
      mergeByFields: { values: [{ field1: 'id', field2: 'id' }] },
      resolve: 'includeBoth'
    },
    position: [...]
  },
  output: [{ id: '123', status: 'changed' }]
});
```

**Compare Datasets has 3 outputs:**
- Output 0: Items only in Input 1 (new items in current data)
- Output 1: Items only in Input 2 (deleted items — were in old snapshot, not in current)
- Output 2: Items in both but different (changed items)

Use `.output(0)`, `.output(1)`, `.output(2)` to route each category.

---

## Pattern 3: Persistent State with DataTable (Track Processing History)

**Use when:** You need to remember what's been processed, store running totals, or maintain state between workflow executions.

**Key node:** `n8n-nodes-base.dataTable` with `upsert` operation

```javascript
// Save/update a record — creates if new, updates if exists
const saveState = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Save Processing State',
    parameters: {
      resource: 'row',
      operation: 'upsert',
      dataTableId: { mode: 'name', value: 'processing-state' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          itemId: expr('{{ $json.id }}'),
          processedAt: expr('{{ $now.toISO() }}'),
          status: expr('{{ $json.processingResult }}'),
          retryCount: expr('{{ ($json.retryCount || 0) + 1 }}')
        }
      },
      options: { createIfNotExists: true }
    },
    position: [...]
  },
  output: [{ success: true }]
});

// Check if an item was already processed
const checkExists = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Already Processed?',
    parameters: {
      resource: 'row',
      operation: 'rowExists',
      dataTableId: { mode: 'name', value: 'processing-state' },
      filters: {
        conditions: [{ column: 'itemId', value: expr('{{ $json.id }}') }]
      }
    },
    position: [...]
  },
  output: [{ exists: true }]
});
```

**DataTable operations cheat sheet:**
| Operation | Purpose |
|-----------|---------|
| `insert` | Add a new row |
| `upsert` | Insert or update (match by field) — **most useful for state** |
| `get` | Retrieve rows (with filters, sorting, pagination) |
| `update` | Update existing rows matching filter |
| `deleteRows` | Delete rows matching filter |
| `rowExists` | **Routes items that ARE in the table** (2 outputs: exists / doesn't exist) |
| `rowNotExists` | **Routes items that are NOT in the table** (2 outputs: not exists / exists) |

**`rowExists` and `rowNotExists` are routing nodes** — they have 2 outputs like an If node. Use `.output(0)` for matches and `.output(1)` for non-matches.

---

## Pattern 4: Human-in-the-Loop Approval

**Use when:** A workflow step requires human review before proceeding (e.g., approve expense, review content, confirm action).

### Option A: Wait Node with Form (built-in)

```javascript
const waitForApproval = node({
  type: 'n8n-nodes-base.wait',
  version: 1.1,
  config: {
    name: 'Wait for Manager Approval',
    parameters: {
      resume: 'form',
      formTitle: 'Approval Required',
      formDescription: expr('Please review: {{ $json.summary }}'),
      formFields: {
        values: [
          { fieldLabel: 'Decision', fieldType: 'dropdown', fieldOptions: { values: [{ option: 'Approve' }, { option: 'Reject' }] }, requiredField: true },
          { fieldLabel: 'Comments', fieldType: 'textarea', requiredField: false }
        ]
      }
    },
    position: [...]
  },
  output: [{ body: { Decision: 'Approve', Comments: 'Looks good' } }]
});
```

**How it works:** The workflow pauses and n8n generates a form URL. Send this URL to the approver (via Slack, email, etc.). When they submit the form, the workflow resumes with their response.

### Option B: Slack/Email/Teams sendAndWait (HITL tools)

Several service nodes have a `sendAndWait` operation that sends a message with approval buttons and pauses until the user responds:

```javascript
// Slack: Send message with Approve/Reject buttons
const slackApproval = node({
  type: 'n8n-nodes-base.slack',
  version: 2.4,
  config: {
    name: 'Ask Slack for Approval',
    parameters: {
      resource: 'message',
      operation: 'sendAndWait',
      channelId: { mode: 'name', value: '#approvals' },
      text: expr('New expense: {{ $json.amount }} by {{ $json.employee }}. Approve?')
    },
    credentials: { slackOAuth2Api: newCredential('Slack') },
    position: [...]
  },
  output: [{ approved: true }]
});
```

**Services with `sendAndWait`:** Slack, Gmail, Microsoft Teams, Microsoft Outlook, Telegram, WhatsApp, Discord

### Routing after approval:

```javascript
const checkDecision = ifElse({
  version: 2.2,
  config: {
    name: 'Approved?',
    parameters: {
      conditions: {
        conditions: [
          { id: 'check', leftValue: expr('{{ $json.body.Decision }}'), rightValue: 'Approve', operator: { type: 'string', operation: 'equals' } }
        ]
      }
    },
    position: [...]
  }
});
// .onTrue(processApproved).onFalse(handleRejection)
```

---

## Pattern 5: Incremental Sync (Keep Two Systems in Sync)

**Use when:** Data in System A needs to stay in sync with System B, processing only changes.

```
[Schedule: Every 10 min]
  → [Fetch from System A (all records modified since $lastSync)]
  → [Only New Items (dedup)]
  → [Loop Through Items]
      → [Upsert to System B]
      → [Save to DataTable: sync log]
  → DONE → [Update $lastSync timestamp in DataTable]
```

**Key implementation detail:** Store the last sync timestamp in a DataTable row:

```javascript
// Read last sync time
const getLastSync = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Get Last Sync Time',
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { mode: 'name', value: 'sync-state' },
      filters: { conditions: [{ column: 'key', value: 'lastSync' }] },
      returnAll: false,
      limit: 1
    },
    position: [...]
  },
  output: [{ key: 'lastSync', value: '2026-04-03T09:00:00Z' }]
});

// After processing, update the sync time
const updateLastSync = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Update Sync Time',
    parameters: {
      resource: 'row',
      operation: 'upsert',
      dataTableId: { mode: 'name', value: 'sync-state' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          key: 'lastSync',
          value: expr('{{ $now.toISO() }}'),
          itemsProcessed: expr('{{ $json.processedCount }}')
        }
      }
    },
    position: [...]
  },
  output: [{ success: true }]
});
```

---

## Pattern 6: Audit Trail (Log All Actions)

**Use when:** Compliance requires tracking who did what, when, with what data.

```javascript
const logAction = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log to Audit Trail',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { mode: 'name', value: 'audit-log' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          action: 'lead_enriched',
          workflowName: expr('{{ $workflow.name }}'),
          executionId: expr('{{ $execution.id }}'),
          itemId: expr('{{ $json.id }}'),
          inputData: expr('{{ JSON.stringify($json) }}'),
          timestamp: expr('{{ $now.toISO() }}')
        }
      },
      options: { createIfNotExists: true }
    },
    position: [...]
  },
  output: [{ success: true }]
});
```

Place this after critical operations (data modifications, API calls, notifications) to create an immutable log.

---

## Pattern 7: Multi-Step Form Wizard

**Use when:** You need to collect information across multiple pages/steps before processing.

```
[Form Trigger: Page 1] → [Form: Page 2] → [Form: Page 3] → [Form: Completion] → [Process All Data]
     Contact info            Company info       Requirements        Thank you page        CRM + Email
```

```javascript
const formStart = trigger({
  type: 'n8n-nodes-base.formTrigger',
  version: 2.5,
  config: {
    name: 'Step 1: Contact Info',
    parameters: {
      formTitle: 'Contact Us',
      formFields: {
        values: [
          { fieldLabel: 'Name', fieldType: 'text', requiredField: true },
          { fieldLabel: 'Email', fieldType: 'email', requiredField: true },
          { fieldLabel: 'Phone', fieldType: 'text', requiredField: false }
        ]
      },
      respondWith: 'redirect'
    },
    position: [240, 300]
  },
  output: [{ Name: 'John', Email: 'john@example.com' }]
});

const page2 = node({
  type: 'n8n-nodes-base.form',
  version: 2.5,
  config: {
    name: 'Step 2: Company Info',
    parameters: {
      operation: 'page',
      formTitle: 'Company Details',
      formFields: {
        values: [
          { fieldLabel: 'Company', fieldType: 'text', requiredField: true },
          { fieldLabel: 'Size', fieldType: 'dropdown', fieldOptions: { values: [{ option: '1-10' }, { option: '11-50' }, { option: '50+' }] } }
        ]
      }
    },
    position: [540, 300]
  },
  output: [{ Company: 'Acme', Size: '11-50' }]
});

const completionPage = node({
  type: 'n8n-nodes-base.form',
  version: 2.5,
  config: {
    name: 'Thank You',
    parameters: {
      operation: 'completion',
      formTitle: 'Thank You!',
      formDescription: 'We will be in touch soon.'
    },
    position: [840, 300]
  },
  output: [{}]
});
```

All form data from all pages is available in the final processing node via `$json` (merged from all pages).

---

## Quick Reference: Which Pattern for What

| User Need | Pattern | Key Node |
|-----------|---------|----------|
| "Only process new items" | Cross-execution dedup | removeDuplicates (seen in previous) |
| "What changed since last run?" | Compare old vs new | compareDatasets + dataTable |
| "Save results for next run" | Persistent state | dataTable (upsert) |
| "Manager needs to approve" | Human-in-the-loop | wait (form) or Slack (sendAndWait) |
| "Keep systems in sync" | Incremental sync | dataTable (timestamp) + dedup |
| "Log everything for compliance" | Audit trail | dataTable (insert) |
| "Multi-step form collection" | Form wizard | formTrigger + form (page) + form (completion) |
| "Don't send duplicate emails" | Output dedup | removeDuplicates (input items) |
| "Track processing status" | State machine | dataTable (upsert with status field) |
| "Queue items for batch processing" | Work queue | dataTable (insert) + schedule (read + process) |
