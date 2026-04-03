# Workflow Blueprint Format

Use this format to present workflow designs to users for approval. The blueprint should be clear enough that a non-technical user understands the flow, yet detailed enough for accurate code generation.

## Template

```
WORKFLOW: [Descriptive Name]
PATTERN: [Primary pattern type(s) from workflow-patterns.md]
TRIGGER: [What starts the workflow and when/how]

[ASCII FLOW DIAGRAM]

NODE DETAILS:
1. [Node Name] ([node type])
   - Purpose: [What this node does]
   - Config: [Key parameters]
   - Outputs: {field1, field2, ...}

2. [Node Name] ([node type])
   - Purpose: [What this node does]
   - Config: [Key parameters]
   - Receives: {{$json.field}} from previous node
   - Outputs: {field1, field2, ...}

[... repeat for all nodes]

DATA FLOW:
- [Node A] outputs {fields} → [Node B] uses {{$json.field}}
- [Node B] outputs {fields} → [Node C] uses {{$json.field}}

CREDENTIALS NEEDED:
- [Service Name]: [Credential type] (e.g., Gmail: OAuth2, OpenAI: API Key)

NOTES:
- [Any important considerations, limitations, or alternatives]
```

## ASCII Diagram Conventions

### Linear Chain
```
[Trigger] ──→ [Step 1] ──→ [Step 2] ──→ [Step 3]
```

### Branching (If/Else)
```
                    ┌─ TRUE ──→ [Action A] ──→ [Notify]
[Trigger] ──→ [If] ─┤
                    └─ FALSE ─→ [Action B]
```

### Multi-way Routing (Switch)
```
                        ┌─ Case 0 ──→ [Urgent Handler]
[Trigger] ──→ [Switch] ─┼─ Case 1 ──→ [Normal Handler]
                        └─ Case 2 ──→ [Archive]
```

### Parallel Execution
```
              ┌──→ [Branch A] ──┐
[Trigger] ──→ ┤                 ├──→ [Merge] ──→ [Process]
              └──→ [Branch B] ──┘
```

### Batch Processing
```
                                    ┌──────────────────┐
                                    ▼                  │
[Trigger] ──→ [Fetch All] ──→ [Split Batches] ──→ [Process] ──→ [Next Batch]
                                    │
                                    └─ DONE ──→ [Finalize]
```

### AI Agent
```
[Chat Trigger] ──→ [AI Agent]
                      ├── model: [OpenAI Chat Model]
                      ├── memory: [Simple Memory]
                      └── tools: [Tool 1], [Tool 2], ...
```

### Multi-Trigger Fan-In
```
[Webhook Trigger] ──┐
                    ├──→ [Process] ──→ [Notify]
[Schedule Trigger] ─┘
```

### Error Handling
```
[Trigger] ──→ [Risky Node] ──→ [Success Path]
                   │
                   └─ ERROR ──→ [Error Handler] ──→ [Alert]
```

## Example: Complete Blueprint

```
WORKFLOW: Morning Lead Enrichment Pipeline
PATTERN: Scheduled linear chain
TRIGGER: Every weekday at 8:00 AM

[Schedule Trigger] ──→ [HubSpot: Get New Leads] ──→ [Loop Over Items]
    8:00 AM M-F           contact/getAll                    │
                          limit: 50                         ▼
                          filter: created today     [Clearbit: Enrich] ──→ [Next Batch]
                                                       │
                                                       └─ DONE ──→ [Slack: Post Summary]
                                                                      #sales-leads channel

NODE DETAILS:
1. Schedule Trigger (n8n-nodes-base.scheduleTrigger)
   - Purpose: Fires every weekday at 8 AM
   - Config: rule interval, weekdays only
   - Outputs: {}

2. Get New Leads (n8n-nodes-base.hubspot)
   - Purpose: Fetch today's new contacts from HubSpot
   - Config: resource=contact, operation=getAll, limit=50
   - Outputs: {email, firstname, lastname, company, createdate}

3. Loop Over Items (n8n-nodes-base.splitInBatches)
   - Purpose: Process leads in batches of 10 (Clearbit rate limits)
   - Config: batchSize=10

4. Enrich Lead (n8n-nodes-base.httpRequest)
   - Purpose: Call Clearbit API to enrich lead data
   - Config: GET https://company.clearbit.com/v2/companies/find?domain={{$json.company}}
   - Receives: {{$json.email}}, {{$json.company}}
   - Outputs: {company_name, industry, employee_count, location}

5. Post Summary (n8n-nodes-base.slack)
   - Purpose: Send enriched lead summary to Slack
   - Config: resource=message, operation=sendMessage, channel=#sales-leads
   - Receives: aggregated lead data
   - Outputs: {ok, ts}

DATA FLOW:
- Schedule Trigger fires → HubSpot fetches leads with {email, company}
- Each lead → Clearbit enriches with {industry, employee_count}
- All enriched leads → Slack formats and posts summary message

CREDENTIALS NEEDED:
- HubSpot: HubSpot API Key or OAuth2 — ⚙️ Setup: n8n Credentials → Add → "HubSpot" → paste API key
- Clearbit: API Key (via HTTP Request auth header) — ⚙️ Setup: n8n Credentials → Add → "HTTP Header Auth" → name: Authorization, value: Bearer YOUR_KEY
- Slack: Slack Bot Token (OAuth2) — ⚙️ Setup: n8n Credentials → Add → "Slack OAuth2" → Sign in with Slack

⚠️ These credentials must be configured in n8n BEFORE the workflow can run.
   After building, I'll guide you through setting up each one.

NOTES:
- Clearbit free tier allows 50 lookups/month — consider caching
- If a lead has no company domain, Clearbit lookup will fail — consider adding error handling
```

## Guidelines

1. **Always name nodes descriptively** — "Get New Leads" not "HTTP Request", "Enrich Lead" not "Set"
2. **Show the data shape** at each step — users need to understand what flows between nodes
3. **Note credential requirements with setup hints** — users need to know BEFORE building what they'll need to configure. Include a brief setup hint for each credential (OAuth sign-in, API key copy, etc.)
4. **Flag potential issues** — rate limits, error cases, edge cases the user should know about
5. **Keep diagrams simple** — for 10+ node workflows, group related nodes and show the high-level flow, with details below
6. **Indicate expressions** — show `{{$json.field}}` syntax so users see how data connects
7. **Warn about credential complexity** — If a credential requires OAuth setup or a cloud project (like Google APIs), flag it early so the user can prepare
