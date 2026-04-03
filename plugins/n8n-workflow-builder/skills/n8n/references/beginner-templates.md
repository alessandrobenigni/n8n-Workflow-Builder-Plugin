# Beginner Templates

Pre-researched workflow templates for first-time n8n users. Each template includes the exact nodes, versions, and SDK skeleton needed — skip Phase 2-3 and jump straight to Phase 4 (BUILD).

## When to Use

Activate Beginner Mode when 2+ of these signals are detected:
- Vague requests: "I want to automate something", "what can I do"
- Questions about concepts: "what is a webhook", "how does n8n work"
- Uncertainty: "I'm not sure", "is it possible", "I'm new to this"
- Overly broad: "automate my business", "connect everything"

Present these templates:
> "Let me help you build your first automation! Pick a starter template:"

## Template 1: Daily Slack Reminder

**Description:** Post a message to a Slack channel every morning.
**Complexity:** 2 nodes (simplest possible workflow)
**Credentials:** Slack (OAuth2 or Bot Token)
**Nodes:** scheduleTrigger v1.3, slack v2.4
**Pattern:** Scheduled linear chain

**What to explain to beginner:**
- "A **trigger** is what starts your workflow. Schedule Trigger fires at the time you set."
- "The **Slack node** sends a message. You'll need to connect your Slack account in n8n."
- "After building, we need to **activate** the workflow so the schedule actually fires."

## Template 2: Form to Email

**Description:** When someone submits a form, send an email with the submitted data.
**Complexity:** 2 nodes
**Credentials:** Gmail (OAuth2) or Send Email (SMTP)
**Nodes:** formTrigger v2.5, gmail v2.2 (resource=message, operation=send)
**Pattern:** Event-driven linear

**What to explain:**
- "A **form trigger** creates a web form that anyone can fill out. n8n hosts it for you."
- "When someone submits the form, the workflow runs and sends an email with their answers."
- "**Credentials** are saved logins. You'll connect your Gmail account once, and n8n remembers it."

## Template 3: Webhook to Google Sheets

**Description:** Receive data via HTTP and save each item to a Google Sheet.
**Complexity:** 2 nodes
**Credentials:** Google Sheets (OAuth2)
**Nodes:** webhook v2.1, googleSheets v4.7 (resource=sheet, operation=append)
**Pattern:** Event-driven linear

**What to explain:**
- "A **webhook** is a URL that receives data. Other apps can send data to it."
- "Every time data arrives at the webhook URL, n8n adds a new row to your Google Sheet."
- "You'll need to share your Google Sheet with n8n. The setup wizard walks you through it."

## Template 4: RSS to Slack

**Description:** Monitor an RSS feed and post new items to Slack.
**Complexity:** 3 nodes
**Credentials:** Slack
**Nodes:** scheduleTrigger v1.3, rssFeedRead v1, slack v2.4 (resource=message, operation=post)
**Pattern:** Scheduled linear chain

**What to explain:**
- "**RSS** is a standard way websites publish updates. Blogs, news sites, and podcasts all have RSS feeds."
- "This workflow checks the feed every hour. When there's a new post, it sends a Slack message."
- "Find the RSS URL on the website (usually looks like `example.com/feed` or `example.com/rss`)."

## Template 5: Manual Data Processor

**Description:** Click a button to process data — fetch from an API, transform it, and display results.
**Complexity:** 3 nodes (no credentials needed!)
**Credentials:** None
**Nodes:** manualTrigger v1, httpRequest v4.3, set v3.4
**Pattern:** Manual linear chain

**What to explain:**
- "This is the simplest way to start — click a button and the workflow runs."
- "The **HTTP Request** node calls any public API. We'll use a free one that doesn't need a login."
- "The **Set** node transforms the data into the format you want."
- "No accounts or credentials needed — this is a great way to learn n8n!"

## Beginner Mode Behavior

When activated, adjust all phases:

**Phase 1 (UNDERSTAND):** Instead of extracting services/triggers, offer the template list first.

**Phase 3 (DESIGN):** Add explanatory annotations to the blueprint. Each node gets a plain-English explanation:
> "[Schedule Trigger] — This starts the workflow at the time you choose (like an alarm clock)"
> "[Slack: Post Message] — This sends your message to the Slack channel you pick"

**Phase 6 (DEPLOY):** Always recommend "Keep as draft" for beginners:
> "I've created your workflow as a draft. Here's how to test it:
> 1. Open n8n at http://localhost:5678
> 2. Find '[Name]' in your workflows
> 3. Click 'Test Workflow' in the top right
> 4. Watch the data flow through each node in real-time!
> 5. When you're happy, click 'Activate' to make it run automatically."

**Throughout:** Inline definitions for technical terms:
- **webhook** — a URL that receives data from other services
- **trigger** — the node that starts your workflow (like a doorbell)
- **credential** — saved login details for a service (Gmail, Slack, etc.)
- **expression** — a formula like `{{ $json.email }}` that pulls data from the previous step
- **node** — one step in your workflow (like a building block)
- **execution** — one run of your workflow from start to finish
- **item** — one piece of data flowing through the workflow (like one email, one row)
