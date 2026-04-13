#!/usr/bin/env python3
"""
n8n Claude-in-the-Middle (CITM) Runtime Watcher.

Polls a running n8n instance for workflow executions paused at Wait nodes,
extracts the upstream payload, and spawns a fresh `claude` CLI subprocess to
process it and POST the result back to the resume URL.

Key properties:
- **Generic.** Works with ANY n8n workflow that uses Wait nodes with
  `resume: webhook`. No hardcoded workflow IDs.
- **Parallel.** Multiple paused executions are processed concurrently via
  non-blocking subprocess.Popen, capped at MAX_CONCURRENT_CLAUDES.
- **Singleton.** Only one watcher runs per machine (PID-file lock with
  cross-platform liveness check). Prevents duplicate spawning.
- **Resilient.** Survives n8n restarts, transient API errors, and stale
  state. Tracks handled (exec_id, wait_node) pairs to prevent re-processing.
- **Stateless Claudes.** Each handoff spawns a fresh `claude -p` subprocess
  with empty context. No conversation pollution between handoffs.
- **Convention over configuration.** Payloads must contain a field whose
  key ends in `_instructions` (e.g. `judge_instructions`,
  `draft_instructions`). Claude reads that field for its task brief.

Configuration:
    Reads ~/.claude/n8n-citm/config.json with this shape:

        {
          "n8n_url":      "http://localhost:5678",
          "n8n_api_key":  "<X-N8N-API-KEY value>",
          "claude_bin":   "claude",
          "workflow_ids": ["abc", "def"],   // optional allow-list
          "poll_interval_s": 15,
          "max_concurrent_claudes": 4,
          "claude_timeout_s": 600
        }

    Environment variables override config keys. Useful overrides:
      CITM_CONFIG_DIR  (default: ~/.claude/n8n-citm)
      CITM_N8N_URL
      CITM_N8N_API_KEY
      CITM_CLAUDE_BIN

Usage:
    python3 citm_watcher.py            # foreground, exits after 10 min idle
    python3 citm_watcher.py --daemon   # forever, file logging only
    python3 citm_watcher.py --once     # single poll cycle, then exit
    python3 citm_watcher.py --status   # show running state and exit
    python3 citm_watcher.py --health   # connectivity check and exit

Dependencies: stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(os.environ.get(
    "CITM_CONFIG_DIR",
    str(Path.home() / ".claude" / "n8n-citm"),
))
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "logs" / "watcher.log"
PID_FILE = CONFIG_DIR / "watcher.pid"
PAYLOAD_DIR = CONFIG_DIR / "payloads"

DEFAULT_CONFIG: dict[str, Any] = {
    "n8n_url": "http://localhost:5678",
    "n8n_api_key": "",
    "claude_bin": "claude",
    "workflow_ids": [],          # empty = all workflows
    "poll_interval_s": 15,
    "min_loop_sleep_s": 5,
    "max_concurrent_claudes": 4,
    "claude_timeout_s": 600,
    "scan_window": 50,           # how many IDs to scan ahead per poll
    "scan_back": 10,             # how many IDs back to re-check
    "max_idle_polls": 40,        # foreground exit after this many idle polls
    "payload_keep_completed": True,
}

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_config() -> dict[str, Any]:
    """Load config from disk, merge with defaults, then apply env overrides."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                cfg.update(user)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[citm] config load error: {e}", file=sys.stderr)

    env_map = {
        "CITM_N8N_URL": "n8n_url",
        "CITM_N8N_API_KEY": "n8n_api_key",
        "CITM_CLAUDE_BIN": "claude_bin",
    }
    for env, key in env_map.items():
        val = os.environ.get(env)
        if val:
            cfg[key] = val
    return cfg


# ---------------------------------------------------------------------------
# n8n REST API
# ---------------------------------------------------------------------------


class N8nClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _get(self, path: str, timeout: float = 15.0) -> Any:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={
                "X-N8N-API-KEY": self.api_key,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def health(self) -> bool:
        try:
            urllib.request.urlopen(
                f"{self.base_url}/healthz", timeout=5
            ).read()
            return True
        except Exception:
            return False

    def latest_execution_id(self) -> int:
        try:
            res = self._get("/api/v1/executions?limit=1")
            data = res.get("data") or []
            if data:
                return int(data[0].get("id", 0))
        except Exception:
            pass
        return 0

    def get_execution(self, exec_id: int, with_data: bool = False) -> dict | None:
        path = f"/api/v1/executions/{exec_id}"
        if with_data:
            path += "?includeData=true"
        try:
            return self._get(path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise


# ---------------------------------------------------------------------------
# Singleton lock
# ---------------------------------------------------------------------------


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                creationflags=0x08000000,
                text=True,
                timeout=5,
            )
            return str(pid) in out and "No tasks" not in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_singleton_lock() -> bool:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            old_pid = 0
        if old_pid and _process_alive(old_pid):
            return False
    PID_FILE.write_text(str(os.getpid()))
    return True


def release_singleton_lock() -> None:
    try:
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Wait-node detection
# ---------------------------------------------------------------------------


def find_paused_wait_nodes(execution: dict) -> list[dict]:
    """
    Return a list of paused-Wait descriptors for the given execution. Each
    descriptor has: { wait_name, payload, resume_url, run_index }. Multiple
    Wait nodes can be paused simultaneously (parallel CITM branches).
    """
    out: list[dict] = []
    run_data = (
        execution.get("data", {})
        .get("resultData", {})
        .get("runData", {})
    )
    for node_name, runs in run_data.items():
        if not runs:
            continue
        last = runs[-1]
        status = last.get("executionStatus") or last.get("status")
        if status != "waiting":
            continue
        meta = last.get("metadata") or {}
        resume_url = meta.get("resumeUrl")
        if not resume_url:
            # Wait nodes without metadata.resumeUrl (e.g. time-based waits)
            # are not CITM steps — skip silently.
            continue
        # Pull payload from upstream node via `source`
        payload: dict = {}
        sources = last.get("source") or []
        if sources:
            prev_name = sources[0].get("previousNode")
            prev_out_idx = sources[0].get("previousNodeOutput", 0) or 0
            prev_run_idx = sources[0].get("previousNodeRun", 0) or 0
            prev_runs = run_data.get(prev_name) or []
            if prev_runs and prev_run_idx < len(prev_runs):
                prev = prev_runs[prev_run_idx]
                try:
                    main = prev.get("data", {}).get("main", [])
                    branch = main[prev_out_idx] if prev_out_idx < len(main) else []
                    payload = (branch or [{}])[0].get("json", {})
                except (IndexError, KeyError, TypeError):
                    payload = {}
        out.append({
            "wait_name": node_name,
            "payload": payload,
            "resume_url": resume_url,
            "run_index": len(runs) - 1,
        })
    return out


# ---------------------------------------------------------------------------
# Claude subprocess
# ---------------------------------------------------------------------------


def write_payload_file(exec_id: int, wait_name: str, payload: dict) -> Path:
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_wait = "".join(c if c.isalnum() else "_" for c in wait_name)
    path = PAYLOAD_DIR / f"{exec_id}_{safe_wait}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def build_claude_prompt(payload_path: Path, resume_url: str, wait_name: str) -> str:
    posix_path = str(payload_path).replace("\\", "/")
    return (
        "You are a one-shot automation worker inside an n8n "
        "Claude-in-the-Middle step. There is no user. Do not ask questions, "
        "do not request approval, do not print explanations beyond the final "
        "single-line confirmation.\n\n"
        f"Wait node: {wait_name}\n\n"
        "TASK (execute these steps in order):\n"
        f"1. Read the full payload JSON at: {posix_path}\n"
        "2. Find the field in that payload whose key ends in `_instructions` "
        "(e.g. judge_instructions, draft_instructions, factcheck_instructions). "
        "Read its content carefully — it is your task brief and contains the "
        "exact output JSON schema you must produce.\n"
        "3. Follow those instructions exactly. Produce a single JSON object "
        "matching the output schema.\n"
        "4. Save that JSON to a temp file (anywhere writable).\n"
        "5. POST it to the resume URL via curl with "
        "`Content-Type: application/json`. Use this exact shape:\n"
        f"   curl -s -X POST -H 'Content-Type: application/json' "
        f"--data-binary @<tempfile> '{resume_url}'\n"
        "6. Print ONE short line confirming completion. Then exit.\n\n"
        f"Resume URL: {resume_url}\n"
        "You have the Bash tool. Use it. The workflow will hang forever if "
        "you don't POST in step 5. Output JSON only — no markdown fences, "
        "no commentary outside the JSON object."
    )


def spawn_claude(claude_bin: str, prompt: str) -> subprocess.Popen:
    """
    Spawn a non-blocking claude subprocess. Returns the Popen handle for
    the caller to track.
    """
    creation_flags = 0
    if os.name == "nt":
        creation_flags = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.Popen(
        [claude_bin, "-p", "--dangerously-skip-permissions"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        shell=False,
        creationflags=creation_flags,
    )


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(daemon: bool) -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
    if not daemon:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("citm")


# ---------------------------------------------------------------------------
# In-flight tracking
# ---------------------------------------------------------------------------


class InFlight:
    """Tracks claude subprocesses currently running for paused Wait nodes."""

    def __init__(self, max_concurrent: int, timeout_s: int, log: logging.Logger):
        self.procs: dict[str, dict] = {}  # key -> {proc, started_at, exec_id, wait_name}
        self.max_concurrent = max_concurrent
        self.timeout_s = timeout_s
        self.log = log

    def __len__(self) -> int:
        return len(self.procs)

    def is_inflight(self, key: str) -> bool:
        return key in self.procs

    def has_capacity(self) -> bool:
        return len(self.procs) < self.max_concurrent

    def add(self, key: str, proc: subprocess.Popen, prompt: str,
            exec_id: int, wait_name: str) -> None:
        # Send the prompt over stdin in a non-blocking way by closing stdin
        # right after writing. communicate() in reap() will collect output.
        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt)
            proc.stdin.close()
        except Exception as e:
            self.log.error("[%s] failed to send prompt to claude: %s", key, e)
            try:
                proc.kill()
            except Exception:
                pass
            return
        self.procs[key] = {
            "proc": proc,
            "started_at": time.time(),
            "exec_id": exec_id,
            "wait_name": wait_name,
        }

    def reap(self) -> list[tuple[str, int, str]]:
        """Return a list of (key, returncode, last_stdout_line) for finished claudes."""
        finished: list[tuple[str, int, str]] = []
        now = time.time()
        for key in list(self.procs.keys()):
            entry = self.procs[key]
            proc = entry["proc"]
            elapsed = now - entry["started_at"]
            rc = proc.poll()
            if rc is None and elapsed > self.timeout_s:
                self.log.error(
                    "[%d] claude TIMEOUT after %ds at '%s' — killing",
                    entry["exec_id"], int(elapsed), entry["wait_name"],
                )
                try:
                    proc.kill()
                except Exception:
                    pass
                rc = proc.wait(timeout=5)
            if rc is None:
                continue
            try:
                out, err = proc.communicate(timeout=5)
            except Exception as e:
                self.log.warning("[%s] communicate err: %s", key, e)
                out, err = "", ""
            tail = ""
            if out:
                lines = [l for l in out.strip().splitlines() if l.strip()]
                tail = lines[-1] if lines else ""
            finished.append((key, rc, tail))
            if rc != 0 and err:
                self.log.warning(
                    "[%s] claude stderr: %s", key, (err or "")[:400]
                )
            del self.procs[key]
        return finished


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main_loop(cfg: dict[str, Any], log: logging.Logger,
              run_once: bool = False) -> int:
    client = N8nClient(cfg["n8n_url"], cfg["n8n_api_key"])
    if not client.health():
        log.error("n8n is not reachable at %s/healthz", cfg["n8n_url"])
        return 2

    inflight = InFlight(
        max_concurrent=int(cfg["max_concurrent_claudes"]),
        timeout_s=int(cfg["claude_timeout_s"]),
        log=log,
    )

    handled: set[str] = set()
    workflow_filter = set(cfg.get("workflow_ids") or [])
    watermark_id = client.latest_execution_id()
    log.info(
        "watcher up | n8n=%s | workflows=%s | poll=%ds | "
        "max_concurrent=%d | watermark=%d",
        cfg["n8n_url"],
        ",".join(workflow_filter) if workflow_filter else "ALL",
        cfg["poll_interval_s"],
        cfg["max_concurrent_claudes"],
        watermark_id,
    )

    idle_polls = 0

    while True:
        # 1) Reap any finished claudes
        finished = inflight.reap()
        for key, rc, tail in finished:
            if rc == 0:
                log.info("[%s] claude done: %s", key, tail[:160])
            else:
                log.error("[%s] claude FAILED rc=%s tail=%s", key, rc, tail[:160])
                # Allow retry on next poll cycle
                handled.discard(key)

        # 2) Discover new paused executions
        new_waits = _discover_paused_waits(
            client, workflow_filter, watermark_id, cfg, log
        )
        # Bump watermark to the highest seen ID
        for exe_id, _, _ in new_waits:
            if exe_id > watermark_id:
                watermark_id = exe_id

        # 3) Spawn claude for each new waiting node, respecting capacity
        spawned = 0
        for exe_id, exe_data, waits in new_waits:
            for wait in waits:
                key = f"{exe_id}:{wait['wait_name']}"
                if key in handled or inflight.is_inflight(key):
                    continue
                if not inflight.has_capacity():
                    log.info(
                        "at capacity (%d), deferring [%s]",
                        len(inflight), key,
                    )
                    break
                handled.add(key)
                payload_path = write_payload_file(
                    exe_id, wait["wait_name"], wait["payload"]
                )
                payload_bytes = payload_path.stat().st_size
                if payload_bytes < 50:
                    log.warning(
                        "[%s] payload looks empty (%d bytes) — skipping",
                        key, payload_bytes,
                    )
                    handled.discard(key)
                    continue
                log.info(
                    "[%s] spawning claude (payload %d bytes, url=%s)",
                    key, payload_bytes, wait["resume_url"],
                )
                prompt = build_claude_prompt(
                    payload_path, wait["resume_url"], wait["wait_name"]
                )
                proc = spawn_claude(cfg["claude_bin"], prompt)
                inflight.add(key, proc, prompt, exe_id, wait["wait_name"])
                spawned += 1

        # 4) Sleep / exit logic
        if run_once:
            return 0
        if spawned == 0 and not inflight:
            idle_polls += 1
        else:
            idle_polls = 0
        max_idle = int(cfg["max_idle_polls"])
        if max_idle and idle_polls >= max_idle:
            log.info("idle for %d polls — exiting (foreground mode)", idle_polls)
            return 0
        sleep_for = (
            int(cfg["min_loop_sleep_s"])
            if (spawned or inflight)
            else int(cfg["poll_interval_s"])
        )
        time.sleep(sleep_for)


def _discover_paused_waits(
    client: N8nClient,
    workflow_filter: set,
    watermark: int,
    cfg: dict,
    log: logging.Logger,
) -> list[tuple[int, dict, list[dict]]]:
    """
    Scan forward from watermark for new executions, plus a small back-window
    for state changes on existing ones. Returns a list of
    (exec_id, full_execution_data, list_of_paused_waits) tuples.
    """
    out: list[tuple[int, dict, list[dict]]] = []
    seen_ids: set[int] = set()

    # Forward scan
    next_id = watermark + 1
    consecutive_missing = 0
    scanned = 0
    while scanned < int(cfg["scan_window"]) and consecutive_missing < 3:
        try:
            exe = client.get_execution(next_id, with_data=False)
        except Exception as e:
            log.warning("forward probe id=%d err: %s", next_id, e)
            break
        if exe is None:
            consecutive_missing += 1
            next_id += 1
            scanned += 1
            continue
        consecutive_missing = 0
        seen_ids.add(next_id)
        if _interesting(exe, workflow_filter):
            full = client.get_execution(next_id, with_data=True)
            waits = find_paused_wait_nodes(full or {})
            if waits:
                out.append((next_id, full or {}, waits))
        next_id += 1
        scanned += 1

    # Back scan for state changes
    for back in range(int(cfg["scan_back"])):
        probe_id = watermark - back
        if probe_id <= 0 or probe_id in seen_ids:
            continue
        try:
            exe = client.get_execution(probe_id, with_data=False)
        except Exception:
            continue
        if not _interesting(exe, workflow_filter):
            continue
        try:
            full = client.get_execution(probe_id, with_data=True)
        except Exception:
            continue
        waits = find_paused_wait_nodes(full or {})
        if waits:
            out.append((probe_id, full or {}, waits))
    return out


def _interesting(exe: dict | None, workflow_filter: set) -> bool:
    if not exe:
        return False
    if exe.get("finished"):
        return False
    if exe.get("status") != "waiting":
        return False
    if workflow_filter and exe.get("workflowId") not in workflow_filter:
        return False
    return True


# ---------------------------------------------------------------------------
# Status / health subcommands
# ---------------------------------------------------------------------------


def cmd_status(cfg: dict[str, Any]) -> int:
    print(f"config:        {CONFIG_FILE}")
    print(f"log:           {LOG_FILE}")
    print(f"pid file:      {PID_FILE}")
    print(f"payloads:      {PAYLOAD_DIR}")
    print(f"n8n url:       {cfg['n8n_url']}")
    print(f"workflow_ids:  {cfg.get('workflow_ids') or 'ALL'}")
    print(f"poll interval: {cfg['poll_interval_s']}s")
    print(f"max_parallel:  {cfg['max_concurrent_claudes']}")
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            alive = _process_alive(pid)
            print(f"watcher pid:   {pid} {'(alive)' if alive else '(dead)'}")
        except Exception:
            print("watcher pid:   (corrupt pid file)")
    else:
        print("watcher pid:   (not running)")
    return 0


def cmd_health(cfg: dict[str, Any]) -> int:
    client = N8nClient(cfg["n8n_url"], cfg["n8n_api_key"])
    print(f"n8n url:       {cfg['n8n_url']}")
    if not client.health():
        print("n8n /healthz:  FAIL")
        return 2
    print("n8n /healthz:  OK")
    try:
        latest = client.latest_execution_id()
        print(f"latest exec:   {latest}")
    except Exception as e:
        print(f"executions:    FAIL ({e})")
        return 2
    claude_bin = cfg["claude_bin"]
    try:
        out = subprocess.check_output(
            [claude_bin, "--version"], text=True, timeout=10
        ).strip()
        print(f"claude cli:    OK ({out})")
    except FileNotFoundError:
        print(f"claude cli:    NOT FOUND ({claude_bin})")
        return 3
    except Exception as e:
        print(f"claude cli:    ERROR ({e})")
        return 3
    print("all checks:    OK")
    return 0


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="n8n Claude-in-the-Middle runtime watcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Run forever, file logging only.")
    parser.add_argument("--once", action="store_true",
                        help="Run a single poll cycle and exit.")
    parser.add_argument("--status", action="store_true",
                        help="Print runtime status and exit.")
    parser.add_argument("--health", action="store_true",
                        help="Run connectivity checks and exit.")
    args = parser.parse_args()

    cfg = load_config()

    if args.status:
        return cmd_status(cfg)
    if args.health:
        return cmd_health(cfg)

    if not cfg.get("n8n_api_key"):
        print(
            f"ERROR: n8n_api_key not set. Edit {CONFIG_FILE} or set CITM_N8N_API_KEY.",
            file=sys.stderr,
        )
        return 1

    log = setup_logging(args.daemon)

    if not acquire_singleton_lock():
        log.warning("another watcher is already running — exiting")
        return 0
    try:
        return main_loop(cfg, log, run_once=args.once)
    except KeyboardInterrupt:
        log.info("interrupted")
        return 0
    finally:
        release_singleton_lock()


if __name__ == "__main__":
    sys.exit(main())
