#!/usr/bin/env python3
"""
n8n CITM Runtime — cross-platform installer.

What this does:
  1. Verifies prerequisites (Python 3.8+, claude CLI, n8n reachable).
  2. Prompts for n8n URL + API key (or reads from --n8n-url/--api-key flags).
  3. Writes ~/.claude/n8n-citm/config.json.
  4. Smoke-tests the configuration (fetches /healthz, lists executions).
  5. Registers the watcher as a background service:
       - Windows: Task Scheduler "n8n_citm_watcher" at user logon.
       - macOS:   launchd LaunchAgent ~/Library/LaunchAgents/com.n8n.citm.plist.
       - Linux:   systemd --user unit ~/.config/systemd/user/n8n-citm.service.
  6. Starts the service immediately.
  7. Tails the log and confirms the watcher came up healthy.

Idempotent: safe to re-run. Use --uninstall to remove everything.

Usage:
  python3 install.py
  python3 install.py --n8n-url http://localhost:5678 --api-key <token>
  python3 install.py --uninstall
  python3 install.py --reconfigure   # rewrite config but skip service install
  python3 install.py --check         # run prerequisite checks and exit
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PLUGIN_RUNTIME = Path(__file__).resolve().parent
WATCHER_SCRIPT = PLUGIN_RUNTIME / "citm_watcher.py"
CONFIG_DIR = Path(os.environ.get(
    "CITM_CONFIG_DIR",
    str(Path.home() / ".claude" / "n8n-citm"),
))
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR = CONFIG_DIR / "logs"
LOG_FILE = LOG_DIR / "watcher.log"


def color(s: str, c: str) -> str:
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "bold": "1"}
    if not sys.stdout.isatty() or os.name == "nt":
        return s
    return f"\033[{codes[c]}m{s}\033[0m"


def step(msg: str) -> None:
    print(color(f"==> {msg}", "cyan"))


def ok(msg: str) -> None:
    print(color(f"  OK  {msg}", "green"))


def fail(msg: str) -> None:
    print(color(f"  FAIL  {msg}", "red"), file=sys.stderr)


def warn(msg: str) -> None:
    print(color(f"  WARN  {msg}", "yellow"))


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------


def check_python() -> bool:
    if sys.version_info < (3, 8):
        fail(f"Python 3.8+ required, got {sys.version.split()[0]}")
        return False
    ok(f"Python {sys.version.split()[0]}")
    return True


def find_claude_bin() -> str | None:
    candidates = [
        shutil.which("claude"),
        shutil.which("claude.cmd"),
    ]
    if os.name == "nt":
        npm_root = Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd"
        if npm_root.exists():
            candidates.append(str(npm_root))
    else:
        for p in [Path.home() / ".local" / "bin" / "claude",
                  Path("/usr/local/bin/claude"),
                  Path.home() / "node_modules" / ".bin" / "claude"]:
            if p.exists():
                candidates.append(str(p))
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def check_claude() -> str | None:
    found = find_claude_bin()
    if not found:
        fail("claude CLI not found on PATH or common locations")
        return None
    try:
        ver = subprocess.check_output(
            [found, "--version"], text=True, timeout=10,
        ).strip()
        ok(f"claude CLI: {found} ({ver})")
        return found
    except Exception as e:
        fail(f"claude CLI found at {found} but failed to run: {e}")
        return None


def check_n8n(url: str, api_key: str) -> bool:
    base = url.rstrip("/")
    try:
        urllib.request.urlopen(f"{base}/healthz", timeout=5).read()
        ok(f"n8n /healthz reachable at {base}")
    except Exception as e:
        fail(f"n8n /healthz failed: {e}")
        return False
    if not api_key:
        warn("no api key set yet; skipping API authorization check")
        return True
    try:
        req = urllib.request.Request(
            f"{base}/api/v1/executions?limit=1",
            headers={"X-N8N-API-KEY": api_key, "Accept": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10).read()
        ok("n8n REST API authorized")
        return True
    except urllib.error.HTTPError as e:
        fail(f"n8n REST API returned HTTP {e.code} — check API key")
        return False
    except Exception as e:
        fail(f"n8n REST API request failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Config writer
# ---------------------------------------------------------------------------


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or default


def write_config(n8n_url: str, api_key: str, claude_bin: str,
                 max_parallel: int, workflow_ids: list[str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "n8n_url": n8n_url,
        "n8n_api_key": api_key,
        "claude_bin": claude_bin,
        "workflow_ids": workflow_ids,
        "poll_interval_s": 15,
        "min_loop_sleep_s": 5,
        "max_concurrent_claudes": max_parallel,
        "claude_timeout_s": 600,
        "scan_window": 50,
        "scan_back": 10,
        "max_idle_polls": 0,
        "payload_keep_completed": True,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass
    ok(f"wrote {CONFIG_FILE}")


# ---------------------------------------------------------------------------
# Service registration: per-OS
# ---------------------------------------------------------------------------


def _python_executable() -> str:
    """Return the python interpreter to use for the daemon."""
    # Prefer pythonw on Windows so no console window appears
    if os.name == "nt":
        candidate = Path(sys.executable).with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return sys.executable


def install_windows_task() -> bool:
    pyw = _python_executable()
    script = str(WATCHER_SCRIPT)
    task_name = "n8n_citm_watcher"
    ps = (
        f"$action = New-ScheduledTaskAction -Execute '{pyw}' "
        f"-Argument '\"{script}\" --daemon';"
        "$trigger = New-ScheduledTaskTrigger -AtLogOn "
        "-User \"$env:USERDOMAIN\\$env:USERNAME\";"
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 "
        "-RestartInterval (New-TimeSpan -Minutes 1) "
        "-ExecutionTimeLimit (New-TimeSpan -Hours 0);"
        "$principal = New-ScheduledTaskPrincipal "
        "-UserId \"$env:USERDOMAIN\\$env:USERNAME\" "
        "-LogonType Interactive -RunLevel Limited;"
        f"Register-ScheduledTask -TaskName '{task_name}' -Action $action "
        "-Trigger $trigger -Settings $settings -Principal $principal "
        "-Description 'n8n Claude-in-the-Middle runtime watcher.' -Force | "
        "Out-Null;"
        f"Start-ScheduledTask -TaskName '{task_name}'"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            check=True, capture_output=True, text=True,
        )
        ok(f"registered Task Scheduler task '{task_name}' (at logon)")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"Task Scheduler register failed: {e.stderr or e.stdout}")
        return False


def uninstall_windows_task() -> None:
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Stop-ScheduledTask -TaskName 'n8n_citm_watcher' "
             "-ErrorAction SilentlyContinue; "
             "Unregister-ScheduledTask -TaskName 'n8n_citm_watcher' "
             "-Confirm:$false -ErrorAction SilentlyContinue"],
            capture_output=True,
        )
        ok("removed Task Scheduler task")
    except Exception as e:
        warn(f"task removal: {e}")


def install_macos_launchd() -> bool:
    pyx = _python_executable()
    plist = Path.home() / "Library" / "LaunchAgents" / "com.n8n.citm.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.n8n.citm</string>
  <key>ProgramArguments</key>
  <array>
    <string>{pyx}</string>
    <string>{WATCHER_SCRIPT}</string>
    <string>--daemon</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{LOG_FILE}</string>
  <key>StandardErrorPath</key><string>{LOG_FILE}</string>
</dict>
</plist>
""",
        encoding="utf-8",
    )
    try:
        subprocess.run(["launchctl", "unload", str(plist)],
                       capture_output=True)
        subprocess.run(["launchctl", "load", str(plist)],
                       check=True, capture_output=True, text=True)
        ok(f"loaded LaunchAgent {plist}")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"launchctl load failed: {e.stderr}")
        return False


def uninstall_macos_launchd() -> None:
    plist = Path.home() / "Library" / "LaunchAgents" / "com.n8n.citm.plist"
    try:
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
        if plist.exists():
            plist.unlink()
        ok("removed LaunchAgent")
    except Exception as e:
        warn(f"launchctl: {e}")


def install_linux_systemd() -> bool:
    pyx = _python_executable()
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit = unit_dir / "n8n-citm.service"
    unit.write_text(
        f"""[Unit]
Description=n8n Claude-in-the-Middle watcher
After=network-online.target

[Service]
Type=simple
ExecStart={pyx} {WATCHER_SCRIPT} --daemon
Restart=always
RestartSec=5
StandardOutput=append:{LOG_FILE}
StandardError=append:{LOG_FILE}

[Install]
WantedBy=default.target
""",
        encoding="utf-8",
    )
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"],
                       check=True, capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", "n8n-citm.service"],
                       check=True, capture_output=True)
        subprocess.run(["systemctl", "--user", "restart", "n8n-citm.service"],
                       check=True, capture_output=True)
        ok(f"enabled and started systemd unit {unit}")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"systemctl failed: {e.stderr.decode() if e.stderr else e}")
        return False


def uninstall_linux_systemd() -> None:
    try:
        subprocess.run(["systemctl", "--user", "stop", "n8n-citm.service"],
                       capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", "n8n-citm.service"],
                       capture_output=True)
        unit = Path.home() / ".config" / "systemd" / "user" / "n8n-citm.service"
        if unit.exists():
            unit.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"],
                       capture_output=True)
        ok("removed systemd unit")
    except Exception as e:
        warn(f"systemctl: {e}")


def install_service() -> bool:
    sys_name = platform.system().lower()
    if sys_name == "windows":
        return install_windows_task()
    if sys_name == "darwin":
        return install_macos_launchd()
    if sys_name == "linux":
        return install_linux_systemd()
    fail(f"unsupported OS: {sys_name}")
    return False


def uninstall_service() -> None:
    sys_name = platform.system().lower()
    if sys_name == "windows":
        uninstall_windows_task()
    elif sys_name == "darwin":
        uninstall_macos_launchd()
    elif sys_name == "linux":
        uninstall_linux_systemd()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def smoke_test() -> bool:
    step("running watcher --health to validate end-to-end config")
    try:
        result = subprocess.run(
            [_python_executable(), str(WATCHER_SCRIPT), "--health"],
            capture_output=True, text=True, timeout=30,
        )
        print(result.stdout)
        if result.returncode != 0:
            fail(f"--health returned {result.returncode}")
            print(result.stderr, file=sys.stderr)
            return False
    except Exception as e:
        fail(f"smoke test crashed: {e}")
        return False
    return True


def tail_log_briefly() -> None:
    if not LOG_FILE.exists():
        return
    step("tailing log for ~3s to confirm daemon started")
    deadline = time.time() + 3
    last_size = 0
    while time.time() < deadline:
        try:
            data = LOG_FILE.read_text(encoding="utf-8", errors="replace")
            if len(data) != last_size:
                tail = data.splitlines()[-3:]
                for line in tail:
                    print(f"  log: {line}")
                last_size = len(data)
        except Exception:
            pass
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def cmd_install(args: argparse.Namespace) -> int:
    step("checking prerequisites")
    if not check_python():
        return 1
    claude_bin = check_claude()
    if not claude_bin:
        return 1

    n8n_url = args.n8n_url or os.environ.get(
        "CITM_N8N_URL", "http://localhost:5678"
    )
    api_key = args.api_key or os.environ.get("CITM_N8N_API_KEY", "")

    if not api_key:
        if args.non_interactive:
            fail("--api-key required in --non-interactive mode")
            return 1
        print()
        step("interactive config")
        n8n_url = prompt("n8n URL", n8n_url)
        api_key = prompt("n8n API key (X-N8N-API-KEY)", "")
        if not api_key:
            fail("api key required")
            return 1

    if not check_n8n(n8n_url, api_key):
        return 1

    max_parallel = args.max_parallel or 4
    workflow_ids: list[str] = []
    if args.workflow_id:
        workflow_ids = [w.strip() for w in args.workflow_id.split(",") if w.strip()]

    write_config(n8n_url, api_key, claude_bin, max_parallel, workflow_ids)

    if args.reconfigure:
        ok("reconfigured (service install skipped)")
        return 0

    step("installing background service")
    if not install_service():
        warn("service install failed — you can still run the watcher manually with:")
        print(f"    {_python_executable()} {WATCHER_SCRIPT} --daemon")
        return 2

    if not smoke_test():
        return 3

    tail_log_briefly()

    print()
    print(color("[OK] n8n CITM runtime installed.", "green"))
    print(f"  config: {CONFIG_FILE}")
    print(f"  log:    {LOG_FILE}")
    print()
    print("Manage the daemon:")
    if platform.system().lower() == "windows":
        print("  Start-ScheduledTask -TaskName 'n8n_citm_watcher'")
        print("  Stop-ScheduledTask  -TaskName 'n8n_citm_watcher'")
    elif platform.system().lower() == "darwin":
        print("  launchctl unload ~/Library/LaunchAgents/com.n8n.citm.plist")
        print("  launchctl load   ~/Library/LaunchAgents/com.n8n.citm.plist")
    else:
        print("  systemctl --user restart n8n-citm.service")
        print("  systemctl --user status  n8n-citm.service")
    return 0


def cmd_uninstall(_args: argparse.Namespace) -> int:
    step("uninstalling service")
    uninstall_service()
    if CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
            ok(f"removed {CONFIG_FILE}")
        except OSError as e:
            warn(f"could not remove config: {e}")
    print()
    print(color("[OK] n8n CITM runtime uninstalled.", "green"))
    print(f"  payloads/logs left at: {CONFIG_DIR}")
    return 0


def cmd_check(_args: argparse.Namespace) -> int:
    step("prerequisite check")
    p = check_python()
    c = check_claude()
    cfg_path = CONFIG_FILE
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        n = check_n8n(cfg.get("n8n_url", ""), cfg.get("n8n_api_key", ""))
    else:
        warn(f"no config at {cfg_path}; skipping n8n check")
        n = True
    return 0 if (p and c and n) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="n8n CITM runtime installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--n8n-url", help="n8n base URL (default: http://localhost:5678)")
    parser.add_argument("--api-key", help="n8n public API key")
    parser.add_argument("--workflow-id", help="comma-separated allow-list (default: all)")
    parser.add_argument("--max-parallel", type=int, help="max concurrent claudes (default 4)")
    parser.add_argument("--non-interactive", action="store_true",
                        help="fail instead of prompting for missing inputs")
    parser.add_argument("--reconfigure", action="store_true",
                        help="rewrite config but skip service install")
    parser.add_argument("--check", action="store_true",
                        help="run prerequisite checks and exit")
    parser.add_argument("--uninstall", action="store_true",
                        help="remove the background service and config file")
    args = parser.parse_args()

    if args.uninstall:
        return cmd_uninstall(args)
    if args.check:
        return cmd_check(args)
    return cmd_install(args)


if __name__ == "__main__":
    sys.exit(main())
