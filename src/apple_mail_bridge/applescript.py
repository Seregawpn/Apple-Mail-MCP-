from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


class AppleScriptError(RuntimeError):
    """Raised when osascript fails."""


def quote_applescript(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def run_applescript(script: str) -> str:
    logger.info("[APPLE_MAIL_SCRIPT] osascript start script_len=%s", len(script))
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    logger.info(
        "[APPLE_MAIL_SCRIPT] osascript finish returncode=%s stdout_len=%s stderr_len=%s",
        proc.returncode,
        len(proc.stdout or ""),
        len(proc.stderr or ""),
    )
    if proc.stderr:
        logger.warning("[APPLE_MAIL_SCRIPT] osascript stderr=%s", (proc.stderr or "").strip()[:500])
    if proc.returncode != 0:
        raise AppleScriptError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout.strip()


def run_json_script(script: str):
    output = run_applescript(script)
    if not output:
        return []
    return json.loads(output)
