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
│       └── data/                       # Local database + utilities
│           ├── nodes.db               # 75MB SQLite (Git LFS)
│           ├── search.py              # Search utility
│           ├── generate_tags.py       # Tag builder
│           └── tag_taxonomy.md        # Tag docs
├── README.md
├── LICENSE
└── CLAUDE.md                           # This file
```

## Plugin requires

- n8n instance running with MCP Server enabled
- `.mcp.json` configured with n8n MCP Bearer token
- Python 3 for the search utility (data/search.py)
