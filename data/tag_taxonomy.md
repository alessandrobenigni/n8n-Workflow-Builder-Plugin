# n8n Node Tag Taxonomy

## Design Principles

1. **Tags represent USER INTENT, not node identity** — "I want to send a notification" maps to tag `messaging`, which matches Slack, Gmail, Telegram, etc.
2. **Multiple tags per node** — Slack gets: `messaging, team-communication, notification, channel-management`
3. **Hierarchical intent layers:**
   - **Domain** — What service category (messaging, database, crm, ai, etc.)
   - **Action** — What the user wants to DO (send-message, store-data, transform, trigger, etc.)
   - **Use-case** — Higher-level workflow intent (notification, lead-enrichment, chatbot, scraping, etc.)
4. **Exact-match retrieval** — `WHERE tags LIKE '%messaging%'` is the full query. No FTS, no scoring, no tokens.

## Tag Categories

### Domain Tags (WHAT service area)
```
messaging          — Slack, Teams, Discord, Telegram, WhatsApp, email services
email              — Gmail, Outlook, SendGrid, Mailchimp, SES, SMTP
social-media       — Twitter/X, LinkedIn, Facebook, Reddit, Medium
crm                — HubSpot, Salesforce, Pipedrive, Zoho, Copper
project-management — Jira, Linear, Trello, Asana, ClickUp, Todoist, GitHub Issues
database           — Postgres, MySQL, MongoDB, Redis, Snowflake, BigQuery, DataTable
spreadsheet        — Google Sheets, Excel, Airtable, Baserow, Coda
file-storage       — S3, Google Drive, Dropbox, OneDrive, FTP/SFTP
cloud-infra        — AWS services, Azure, Google Cloud, Cloudflare
ai-llm             — LLM chat models (OpenAI, Anthropic, Gemini, Ollama, etc.)
ai-agent           — AI Agent, Agent Tool, OpenAI Assistant
ai-embedding       — Embeddings providers (OpenAI, Cohere, Ollama, etc.)
ai-vectorstore     — Vector stores (Pinecone, Qdrant, Chroma, etc.)
ai-memory          — Chat memory (Buffer, Redis, Postgres, MongoDB)
ai-retrieval       — Retrievers, rerankers, RAG components
ai-chain           — LLM chains (summarization, Q&A, basic chain)
ai-processor       — Text classifier, sentiment, information extractor, guardrails
ai-document        — Document loaders, text splitters
ai-tool            — Calculator, Code Tool, Think Tool, HTTP Tool, Workflow Tool
ecommerce          — Shopify, Stripe, WooCommerce, PayPal
marketing          — Mailchimp, ConvertKit, ActiveCampaign, Lemlist, Brevo
support            — Zendesk, Freshdesk, Intercom, Help Scout
analytics          — Google Analytics, Segment
scheduling         — Calendar services (Google Calendar, Cal.com, Calendly)
developer          — GitHub, GitLab, Jenkins, CI/CD, SSH
cms                — WordPress, Ghost, Strapi, Contentful, Webflow
productivity       — Notion, Todoist, Google Tasks, Microsoft To Do
voice-sms          — Twilio, Plivo, Vonage, MessageBird
video-audio        — YouTube, Zoom, OpenAI audio/video, Gemini audio/video
form               — Form Trigger, Typeform, JotForm, Formstack
queue              — RabbitMQ, Kafka, AMQP, SQS, SNS
iot                — MQTT, Home Assistant, Philips Hue
security           — Crypto, JWT, Okta, Bitwarden, Guardrails
utility            — Set, Code, HTTP Request, Wait, No Op, Debug
flow-control       — If, Switch, Merge, Filter, Loop, Split, Sort, Limit
data-transform     — Aggregate, Summarize, Remove Duplicates, Compare, Rename
file-process       — Extract from File, Convert to File, Read PDF, Compression, Edit Image
workflow-meta      — Execute Sub-workflow, Sticky Note, Execution Data, Time Saved
```

### Action Tags (WHAT the user wants to DO)
```
send-message       — Send a message/notification to a channel, person, or group
send-email         — Send an email (any provider)
read-data          — Read/fetch/get data from a source
write-data         — Insert/create/write data to a destination
update-data        — Update existing records
delete-data        — Delete records
search             — Search/query for specific records
trigger-on-event   — Start workflow on external event
trigger-on-schedule — Start workflow on a time schedule
trigger-on-form    — Start workflow on form submission
trigger-on-chat    — Start workflow on chat message
trigger-on-webhook — Start workflow on HTTP request
transform-data     — Transform, map, reshape data
filter-data        — Filter, route, branch data by conditions
merge-data         — Combine data from multiple sources
loop-data          — Iterate over items in batches
generate-content   — Generate text, images, audio, video with AI
analyze-text       — Classify, extract, summarize, analyze text
chat-ai            — Conversational AI interaction
file-upload        — Upload files to storage
file-download      — Download files from storage
file-convert       — Convert between file formats
encrypt-sign       — Encrypt, decrypt, sign, verify data
execute-code       — Run custom code (JS/Python)
call-api           — Make HTTP API calls
manage-workflow    — Execute sub-workflows, manage execution
```

### Use-Case Tags (WHAT workflow pattern)
```
notification       — Alert/notify someone about something
lead-enrichment    — Enrich contact/lead data from multiple sources
data-sync          — Sync data between two systems
data-pipeline      — ETL: extract, transform, load data
chatbot            — Conversational AI chatbot
rag                — Retrieval-augmented generation (knowledge base Q&A)
content-generation — Generate text/image/video content
document-processing — Process PDFs, documents, invoices
web-scraping       — Scrape/extract data from websites
form-processing    — Collect and process form submissions
approval-workflow  — Human-in-the-loop approval flows
error-handling     — Handle errors, retries, fallbacks
monitoring         — Monitor systems, check health, alert on issues
report-generation  — Generate and send reports
social-posting     — Post content to social media
crm-automation     — Automate CRM workflows (leads, deals, contacts)
support-automation — Automate support ticket handling
```

## Tag Assignment Rules

1. Every node gets 3-8 tags (domain + action + use-case)
2. Trigger nodes always get their specific `trigger-on-*` tag
3. Tool variant nodes inherit all tags from their base node + add `ai-tool`
4. Community nodes get tagged based on their `ai_documentation_summary` + `description`
5. Tags are stored as comma-separated lowercase string: `"messaging, send-message, notification, team-communication"`
