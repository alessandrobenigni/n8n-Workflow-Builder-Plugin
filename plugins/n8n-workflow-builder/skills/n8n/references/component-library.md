# Reusable Component Library

Pre-built workflow patterns that ship with the plugin. Use `components.py` to search, get, and insert these into workflows.

## How to Use Components

### During workflow building (Phase 2.5)

Before designing from scratch, check if saved components match:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/components.py --search "error handling"
```

If a match is found, get the full code:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/components.py --get "Error Handler with Slack Alert"
```

Insert the component's SDK code into the workflow being built.

### Saving new components (Phase 8)

After building a useful pattern, offer to save:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/data/components.py --save "My Pattern" \
  --category "error-handling" \
  --description "Catches errors and sends Slack alert" \
  --code 'const errorHandler = node({...});' \
  --params '["slackChannel"]'
```

## Pre-Seeded Components

These ship with the plugin and are available immediately.

### 1. Error Handler with Slack Alert
**Category:** error-handling
**Description:** Catches errors on any node via onError and posts a formatted alert to Slack with workflow name, node name, error message, and timestamp.
**Params:** slackChannel

### 2. Retry with Exponential Backoff
**Category:** error-handling
**Description:** HTTP Request node configured with built-in retry (3 attempts, exponential backoff, 15s timeout).
**Params:** url, method

### 3. Webhook Input Validator
**Category:** input-validation
**Description:** Code node that validates incoming webhook JSON against a schema (required fields, types). Returns 400 on invalid input.
**Params:** requiredFields

### 4. Pagination Loop
**Category:** data-fetching
**Description:** HTTP Request inside a Loop that follows cursor/offset pagination until no more pages.
**Params:** baseUrl, pageSize

### 5. Rate Limiter
**Category:** flow-control
**Description:** SplitInBatches with a Wait node between batches to respect API rate limits.
**Params:** batchSize, delaySeconds

### 6. Deduplication Check
**Category:** data-quality
**Description:** Code node that compares incoming items against a DataTable to skip already-processed items. Uses a unique key field.
**Params:** tableName, uniqueField

### 7. Audit Logger
**Category:** observability
**Description:** Set + DataTable combo that logs workflow execution metadata (inputs, outputs, timestamp, execution ID) for audit trails.
**Params:** tableName

### 8. Dead Letter Queue
**Category:** error-handling
**Description:** Failed items are captured with error details and saved to a DataTable for manual review and reprocessing.
**Params:** tableName

## Categories

| Category | Purpose |
|----------|---------|
| error-handling | Retry, alert, dead letter, circuit breaker |
| input-validation | Schema validation, sanitization |
| data-fetching | Pagination, batching, caching |
| flow-control | Rate limiting, deduplication, conditional routing |
| data-quality | Dedup, validation, cleansing |
| observability | Logging, audit trail, metrics |
| notification | Slack, email, SMS alerts |
| security | Auth validation, data masking |
