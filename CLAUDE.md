# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Purpose

This is a Claude Code plugin marketplace containing the **n8n Workflow Builder** plugin — a conversational n8n workflow builder with Agent Mode.

## Architecture

```
n8n-plugin/                              # Marketplace repository
├── .claude-plugin/
│   └── marketplace.json                 # Marketplace catalog
├── plugins/
│   └── n8n-workflow-builder/            # The plugin
│       ├── .claude-plugin/plugin.json   # Plugin metadata
│       ├── skills/                      # 4 slash commands
│       │   ├── n8n/                     # /n8n — build workflows
│       │   ├── n8n-agent/              # /n8n-agent — Claude as AI brain
│       │   ├── n8n-manage/            # /n8n-manage — lifecycle management
│       │   └── n8n-browse/            # /n8n-browse — explore nodes
│       ├── agents/                     # 4 specialist agents
│       │   ├── n8n-node-researcher.md  # Parallel node discovery
│       │   ├── n8n-code-writer.md     # SDK code generation
│       │   ├── n8n-tool-builder.md    # Tool workflow builder
│       │   └── n8n-validator.md       # Validation fix loop
│       ├── data/                       # Local database + utilities
│       │   ├── nodes.db               # 75MB SQLite (Git LFS)
│       │   ├── search.py              # Search utility
│       │   ├── components.py          # Reusable component library
│       │   ├── prompts.py             # Layered prompt loader
│       │   ├── prompts/               # Prompt library (primitives)
│       │   ├── generate_tags.py       # Tag builder
│       │   └── tag_taxonomy.md        # Tag docs
│       └── runtime/                    # CITM background daemon
│           ├── citm_watcher.py        # Auto-spawns claude on Wait nodes
│           ├── install.py             # Cross-platform installer
│           └── README.md              # Runtime architecture + usage
├── README.md
├── LICENSE
└── CLAUDE.md                           # This file
```

## Plugin requires

- n8n instance running with MCP Server enabled
- `.mcp.json` configured with n8n MCP Bearer token
- Python 3.8+ for search.py, prompts.py, and the CITM runtime
- `claude` CLI on PATH (for the CITM runtime to spawn worker processes)

## CITM runtime

The `plugins/n8n-workflow-builder/runtime/` directory ships a
background watcher that automates Claude-in-the-Middle: it polls n8n
for executions paused at Wait nodes, extracts the upstream payload,
and spawns a fresh `claude -p` subprocess per handoff that processes
the task and POSTs the result back to the signed resume URL.

Install once with `python3 runtime/install.py` and it registers as a
user service (Task Scheduler / launchd / systemd). After that, any
workflow that (a) uses a Wait node with `resume: webhook` and (b) has
an upstream field whose key ends in `_instructions` will be handled
fully automatically — click Execute in the n8n UI and walk away.
Multiple paused Wait nodes (parallel branches, or multiple workflows
at once) are processed concurrently via non-blocking subprocess
spawning, capped by `max_concurrent_claudes` in the config.

See `plugins/n8n-workflow-builder/runtime/README.md` for the full
architecture, workflow design patterns, and troubleshooting guide.
