# n8n Claude-in-the-Middle (CITM) Runtime

Auto-spawn fresh `claude` CLI subprocesses whenever an n8n workflow pauses
at a Wait node. No manual copy-pasting of payloads. No external API keys.
No token billing. The runtime polls n8n, detects paused executions,
extracts the upstream payload, hands it to a one-shot Claude, and
Claude POSTs the JSON result back to the workflow's signed resume URL.

Your main Claude Code session is never touched — each handoff runs in its
own context, exits, and leaves no trace in your conversation.

## Why this exists

Out of the box, Claude-in-the-Middle is a manual workflow: you run the
workflow, see a Wait node pause, copy the payload from the n8n UI, paste
it into Claude, ask Claude to process and POST back. Works, but requires
a human at the keyboard.

This runtime automates that loop entirely. Click "Execute" in the n8n UI,
walk away. Every Wait node in the workflow gets its own fresh Claude and
resolves in the background.

## What it does, step by step

```
         ┌───────────────────────┐
         │  n8n workflow runs    │
         │  hits Wait node       │
         │  generates signed URL │
         └──────────┬────────────┘
                    │ status: waiting
                    ▼
         ┌───────────────────────┐
         │   CITM watcher daemon │
         │   polls every 15s     │
         │   detects new wait    │
         └──────────┬────────────┘
                    │ extracts payload
                    │ from upstream node
                    ▼
         ┌───────────────────────┐
         │ fresh `claude -p`     │
         │ subprocess (empty     │
         │ context, stateless)   │
         │                       │
         │ reads payload file    │
         │ follows instructions  │
         │ curl POST result      │
         └──────────┬────────────┘
                    │ webhook-waiting/<exec>?signature=...
                    ▼
         ┌───────────────────────┐
         │ n8n resumes execution │
         │ next node runs        │
         └───────────────────────┘
```

Multiple Wait nodes in parallel branches? Each gets its own Claude
subprocess, up to `max_concurrent_claudes` at a time. Multiple workflows
paused simultaneously? Same, handled in parallel.

## Installation

Requires Python 3.8+, n8n with REST API enabled, and the `claude` CLI on
PATH.

```bash
# from the plugin directory:
python3 runtime/install.py
```

The installer:

1. Checks prerequisites (Python, claude CLI, n8n reachability)
2. Prompts for your n8n URL and API key (or pass as flags)
3. Writes `~/.claude/n8n-citm/config.json`
4. Smoke-tests the config
5. Registers a background service:
   - **Windows** — Task Scheduler task `n8n_citm_watcher` at user logon
   - **macOS** — launchd LaunchAgent `~/Library/LaunchAgents/com.n8n.citm.plist`
   - **Linux** — systemd user unit `~/.config/systemd/user/n8n-citm.service`
6. Starts the daemon and tails the log to confirm it came up

Non-interactive install:

```bash
python3 runtime/install.py \
  --n8n-url http://localhost:5678 \
  --api-key "$N8N_API_KEY" \
  --max-parallel 4 \
  --non-interactive
```

Restrict to specific workflows (comma-separated IDs):

```bash
python3 runtime/install.py --workflow-id abc123,def456
```

Re-run to reconfigure (safe, idempotent). Remove with:

```bash
python3 runtime/install.py --uninstall
```

## Designing a workflow that uses CITM

The runtime is **convention-based**: any workflow that follows these two
rules will "just work" once the daemon is running.

### Rule 1. Use a Wait node with `resume: webhook`

Add a Wait node with these parameters:

```javascript
const waitForClaude = node({
  type: 'n8n-nodes-base.wait', version: 1.1,
  config: {
    name: 'Wait for Claude Judge',          // any descriptive name
    parameters: {
      resume: 'webhook',
      httpMethod: 'POST',
      incomingAuthentication: 'none',
    },
    position: [x, y],
  },
  output: [{ body: { /* your expected response shape */ } }],
});
```

### Rule 2. The node immediately before Wait outputs a payload with an `<something>_instructions` field

The runtime reads the upstream node's JSON output and passes it verbatim
to Claude. It looks for any top-level key ending in `_instructions`. The
content of that field is Claude's task brief — it must contain the
exact output JSON schema Claude should produce.

A typical "Build Payload" Code node:

```javascript
// in a Code node with mode: runOnceForAllItems
const upstream = $json;
const instructions = $('Read judge.md').first().json.content;

return [{
  json: {
    target_window: upstream.target_window,
    items: upstream.items,
    recent_angles: upstream.recent_angles,
    judge_instructions: instructions,   // <-- this key drives Claude
  },
}];
```

Your `judge.md` prompt file defines the task + the exact JSON shape to return:

```markdown
## Your task
Score each item on 4 dimensions, 1-5 each. Pick the top 3.

## Output format (strict JSON)
{
  "scored": [ { "id": "...", "score": 0, "angle_tag": "..." } ],
  "selected": ["id1", "id2", "id3"],
  "error": null
}
```

That's it. No SDK, no Anthropic API key, no manual clicks. Claude reads
the payload, follows the instructions, POSTs the JSON back, exits.

### Supported field-name conventions

Any key ending in `_instructions` works. Common names:

- `judge_instructions`
- `draft_instructions`
- `factcheck_instructions`
- `analysis_instructions`
- `classify_instructions`
- `extract_instructions`
- `score_instructions`

Pick whichever makes the most sense for your workflow. The runtime is
agnostic.

## Parallel CITM branches

If your workflow fans out into parallel branches, each with its own Wait
node, the runtime spawns one Claude per paused branch, up to
`max_concurrent_claudes` at a time. Each Claude has a fresh context
window — no contamination between branches.

Example: a classification workflow that scores 20 items in parallel
sub-batches, each with its own Wait node, all resolved by independent
Claudes simultaneously.

## Configuration reference

`~/.claude/n8n-citm/config.json`:

```json
{
  "n8n_url": "http://localhost:5678",
  "n8n_api_key": "<X-N8N-API-KEY value>",
  "claude_bin": "claude",
  "workflow_ids": [],
  "poll_interval_s": 15,
  "min_loop_sleep_s": 5,
  "max_concurrent_claudes": 4,
  "claude_timeout_s": 600,
  "scan_window": 50,
  "scan_back": 10,
  "max_idle_polls": 0
}
```

Field meanings:

| field | purpose |
|---|---|
| `n8n_url` | base URL of your n8n instance |
| `n8n_api_key` | X-N8N-API-KEY header value (n8n Public API key) |
| `claude_bin` | path to the `claude` CLI (absolute or on PATH) |
| `workflow_ids` | allow-list of workflow IDs. Empty = all workflows |
| `poll_interval_s` | how often to poll n8n when idle |
| `min_loop_sleep_s` | minimum sleep when there is in-flight work |
| `max_concurrent_claudes` | cap on parallel Claude subprocesses |
| `claude_timeout_s` | kill a Claude subprocess after this many seconds |
| `scan_window` | how many execution IDs to scan ahead per poll |
| `scan_back` | how many IDs back to re-check for state changes |
| `max_idle_polls` | foreground auto-exit; 0 = never exit (daemon mode) |

Environment variables override config keys at runtime:
`CITM_N8N_URL`, `CITM_N8N_API_KEY`, `CITM_CLAUDE_BIN`, `CITM_CONFIG_DIR`.

## Operating the watcher

### Status and health

```bash
python3 runtime/citm_watcher.py --status    # show config, pid, paths
python3 runtime/citm_watcher.py --health    # test n8n + claude connectivity
python3 runtime/citm_watcher.py --once      # run a single poll cycle and exit
```

### Log tail

```bash
# Windows
powershell Get-Content ~\.claude\n8n-citm\logs\watcher.log -Tail 30 -Wait

# macOS/Linux
tail -f ~/.claude/n8n-citm/logs/watcher.log
```

Every paused Wait node shows up as:

```
2026-04-13 13:51:22 INFO [7:Wait for Claude Judge] spawning claude (payload 17485 bytes, url=http://localhost:5678/webhook-waiting/7?signature=...)
2026-04-13 13:52:52 INFO [7:Wait for Claude Judge] claude done: CITM #1 judge complete. Scored 14 items; selected top 3: n45...
```

### Payloads on disk

Payload files are written to `~/.claude/n8n-citm/payloads/<execId>_<WaitName>.json`
so you can inspect what Claude received if a handoff misbehaves.

### Daemon control

```bash
# Windows
Start-ScheduledTask -TaskName 'n8n_citm_watcher'
Stop-ScheduledTask  -TaskName 'n8n_citm_watcher'
Get-ScheduledTask   -TaskName 'n8n_citm_watcher' | Format-List State

# macOS
launchctl load   ~/Library/LaunchAgents/com.n8n.citm.plist
launchctl unload ~/Library/LaunchAgents/com.n8n.citm.plist
launchctl list | grep com.n8n.citm

# Linux
systemctl --user restart n8n-citm.service
systemctl --user stop    n8n-citm.service
systemctl --user status  n8n-citm.service
```

## Troubleshooting

### Claude responds with "I'm ready to help. What would you like me to do?"

The prompt wasn't delivered. Causes:
- `claude` CLI version too old (doesn't support stdin with `-p`)
- Subprocess stdin encoding issue — check `~/.claude/n8n-citm/logs/watcher.log`
  for `claude stderr` lines

### Claude's POST returns "Invalid token"

The resume URL is missing its signature query parameter. The runtime
extracts the signed URL from `runData[waitName][-1].metadata.resumeUrl`
automatically — if it's missing, the Wait node probably isn't in
`resume: webhook` mode.

### Watcher doesn't detect a paused execution

The n8n public API `status=waiting` filter is unreliable on some versions.
The watcher works around this by probing execution IDs directly from a
watermark. If executions still don't appear, run:

```bash
python3 runtime/citm_watcher.py --status
python3 runtime/citm_watcher.py --health
```

### Multiple Claudes spawn for the same Wait node

Singleton lock protects against multiple watcher daemons. If you see
duplicate spawns, run `--status` to check for stale PID files and make
sure only one daemon is registered with your OS service manager.

### "another watcher is already running"

Legitimate — you're already protected. Check the PID file:

```bash
cat ~/.claude/n8n-citm/watcher.pid
```

If the PID is dead, delete the file and restart:

```bash
rm ~/.claude/n8n-citm/watcher.pid
# Windows
Start-ScheduledTask -TaskName 'n8n_citm_watcher'
# macOS
launchctl unload ~/Library/LaunchAgents/com.n8n.citm.plist && \
launchctl load   ~/Library/LaunchAgents/com.n8n.citm.plist
# Linux
systemctl --user restart n8n-citm.service
```

## Security notes

- The config file is written with `0600` permissions on POSIX. It contains
  your n8n API key — treat it like a password.
- Claude subprocesses run with `--dangerously-skip-permissions` so they can
  `curl` the resume URL without prompting. They run with your user
  privileges and can execute any Bash command. Do not install this on a
  machine that runs untrusted n8n workflows — a malicious workflow
  payload could instruct Claude to do anything your user can do.
- The resume URL is cryptographically signed by n8n. Stale URLs from
  retried executions are automatically rejected with "Invalid token".

## Implementation notes (for contributors)

- **Singleton.** `~/.claude/n8n-citm/watcher.pid` holds the running
  watcher's PID. The lock is validated with OS-level liveness checks
  (`tasklist` on Windows, `kill -0` on POSIX).
- **Parallel.** Claudes are spawned via `subprocess.Popen` and tracked in
  a dict keyed by `{exec_id}:{wait_node_name}`. Each poll cycle reaps
  finished processes and dispatches new ones up to the concurrency cap.
- **Watermark scan.** The public API list endpoint hides `waiting`
  executions on some n8n versions, so the watcher scans execution IDs
  directly from `latest_id + 1` forward, plus a small back-window for
  state changes on existing executions.
- **Payload extraction.** Wait nodes do NOT store inputData. The watcher
  reads `runData[waitName][-1].source[0].previousNode`, then pulls that
  upstream node's output from `runData[upstreamName][-1].data.main[0][0].json`.
- **Resume URL.** Extracted from `runData[waitName][-1].metadata.resumeUrl`
  which contains the n8n-generated signature.
