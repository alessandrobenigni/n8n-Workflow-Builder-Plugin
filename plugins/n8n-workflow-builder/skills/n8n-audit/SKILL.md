---
name: n8n-audit
description: >-
  Audit an n8n workflow for security issues, missing best practices, and
  reliability problems. Checks for hardcoded secrets, missing error handling,
  HTTP timeouts, and more. Rates workflow health A through F.
triggers:
  - n8n audit
  - n8n-audit
  - audit workflow
  - check workflow
  - workflow health
  - security check
  - best practices
  - review workflow
  - workflow review
  - is my workflow safe
  - workflow quality
---

# n8n Workflow Audit

You audit existing n8n workflows for security, reliability, best practices, and performance issues. You produce a graded report (A-F) with specific findings and fix instructions.

**Important:** Do NOT call `mcp__n8n-mcp__get_node_types` or `mcp__n8n-mcp__search_nodes` — they are broken. Use `search.py` for node lookups.

## Process

### Step 1: Identify the workflow

Ask: **"Which workflow should I audit? (name or ID)"**

Search for it:
```
mcp__n8n-mcp__search_workflows(query)
```
- If no results: "No workflows match '[query]'. Use `/n8n-manage list` to see all workflows."
- If multiple results: Show the list and ask user to pick one.

Then load the full details:
```
mcp__n8n-mcp__get_workflow_details(workflowId)
```

### Step 2: Run the audit checklist

Analyze the workflow JSON systematically. For each check, note PASS or FAIL with details.

#### Security Checks (weight: 3 points each)

| ID | Check | How to Detect | Severity |
|----|-------|--------------|----------|
| S1 | **Hardcoded secrets** | Scan all parameter values for strings matching: `sk-*`, `xoxb-*`, `xoxp-*`, `Bearer *`, `Basic *`, `ghp_*`, `gho_*`, strings >32 chars of hex/base64 | CRITICAL |
| S2 | **Unauthenticated webhooks** | Webhook nodes with `incomingAuthentication: 'none'` on public-facing paths | HIGH |
| S3 | **HTTP (not HTTPS)** | HTTP Request nodes with URLs starting with `http://` (not `https://`), excluding `localhost` and `127.0.0.1` | HIGH |
| S4 | **Unsafe code execution** | Code nodes containing `eval(`, `Function(`, `require(`, `child_process` | CRITICAL |
| S5 | **Missing credential usage** | Nodes that should use `newCredential()` but have inline auth headers | HIGH |

#### Reliability Checks (weight: 2 points each)

| ID | Check | How to Detect | Severity |
|----|-------|--------------|----------|
| R1 | **No error handling on HTTP nodes** | HTTP Request nodes without `onError: 'continueErrorOutput'` | HIGH |
| R2 | **Missing timeout on HTTP nodes** | HTTP Request nodes without `options.timeout` | MEDIUM |
| R3 | **No error handling anywhere** | Zero nodes with error output connections in the entire workflow | HIGH |
| R4 | **Batch processing without error handling** | SplitInBatches node present but no error branches | MEDIUM |
| R5 | **Schedule trigger on inactive workflow** | Schedule/Cron trigger but workflow is not active | HIGH |

#### Best Practice Checks (weight: 1 point each)

| ID | Check | How to Detect | Severity |
|----|-------|--------------|----------|
| B1 | **Generic node names** | Nodes named "HTTP Request", "Code", "Set", "If", "Switch" (default names) | LOW |
| B2 | **No sticky notes** | Zero sticky note nodes in the workflow | LOW |
| B3 | **Missing workflow description** | Workflow has no description or empty description | LOW |
| B4 | **Excessive chain length** | More than 15 nodes in a linear chain with no branching | MEDIUM |
| B5 | **Disconnected nodes** | Nodes in the JSON that have no incoming or outgoing connections | LOW |

#### Performance Checks (weight: 1 point each)

| ID | Check | How to Detect | Severity |
|----|-------|--------------|----------|
| P1 | **No pagination on large API calls** | HTTP Request or service nodes doing `getAll` without limit or pagination | MEDIUM |
| P2 | **Missing executeOnce** | Two independent data sources chained (second runs N times unnecessarily) | MEDIUM |
| P3 | **Oversized batch** | SplitInBatches with batchSize > 100 and no rate limiting | LOW |

### Step 3: Calculate the grade

**Maximum points:** (Security checks * 3) + (Reliability checks * 2) + (Best practice checks * 1) + (Performance checks * 1)

**Points earned:** Max points minus deductions for each FAIL (deduction = check weight)

**Grade:**
- **A** (90-100%): Exemplary — production ready
- **B** (75-89%): Good — minor improvements recommended
- **C** (60-74%): Acceptable — several issues to address
- **D** (40-59%): Poor — significant problems
- **F** (0-39%): Critical — should not run in production

### Step 4: Generate the report

```
WORKFLOW AUDIT: [Workflow Name] ([id])
GRADE: [A-F] ([percentage]%)
STATUS: [Active/Draft] | NODES: [count] | PATTERN: [type]

CRITICAL (fix immediately):
- [S1] Node "[name]": Hardcoded string "sk-abc1..." appears to be an API key.
  FIX: Create an HTTP Header Auth credential in n8n and use newCredential().

WARNINGS (should fix):
- [R1] Node "[name]": No error handling. API failures will crash the workflow.
  FIX: Add onError: 'continueErrorOutput' and an error branch.
- [R2] Node "[name]": No timeout. Could hang indefinitely.
  FIX: Add options.timeout: 15000 (15 seconds).

SUGGESTIONS (nice to have):
- [B1] 3 nodes have generic names. Use descriptive names for clarity.
- [B2] No sticky notes. Add documentation for future maintainers.

PASSED: [list of passing checks]

SUMMARY: [X] critical, [Y] warnings, [Z] suggestions out of [N] checks.
```

### Step 5: Offer to fix

For each fixable issue, offer to apply the fix:
> "Want me to fix these issues? I can:
> 1. Add error handling to all HTTP Request nodes
> 2. Replace hardcoded secrets with n8n credentials
> 3. Rename generic nodes to descriptive names
> 4. Add timeout to HTTP Request nodes"

If user says yes, use `/n8n` to update the workflow with the fixes applied.

### Step 6: Check recent executions (optional enrichment)

If available, check recent execution for additional insights:
```
mcp__n8n-mcp__get_execution(workflowId, executionId, includeData: true)
```
Look for: frequent error nodes, slow nodes, large data volumes.
