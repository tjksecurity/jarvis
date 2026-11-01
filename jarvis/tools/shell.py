"""Local shell command execution. Every command requires operator authorization."""
from __future__ import annotations

import subprocess

from .base import Tool, ToolContext, ToolResult

MAX_OUTPUT = 100_000


def _shell_exec(tool_input: dict, ctx: ToolContext) -> ToolResult:
    command = tool_input.get("command", "").strip()
    if not command:
        return ToolResult("command is required", is_error=True)
    timeout = int(tool_input.get("timeout", 60))
    cwd = tool_input.get("cwd")
    workdir = ctx.workspace
    if cwd:
        from pathlib import Path
        p = Path(cwd).expanduser()
        if not p.is_absolute():
            p = ctx.workspace / p
        workdir = p.resolve()

    # Arbitrary shell syntax cannot be classified safely by a token blacklist.
    # Approval comes only from the operator callback, never from model input.
    detail = f"$ {command}\ncwd={workdir}\ntimeout={timeout}s"
    try:
        approved = ctx.confirm_destructive("shell_exec", detail)
    except (Exception, KeyboardInterrupt):
        return ToolResult("[FAIL] operator authorization unavailable for shell_exec.", is_error=True)
    if approved is not True:
        return ToolResult("[FAIL] operator declined shell_exec.", is_error=True)

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(f"[FAIL] command timed out after {timeout}s", is_error=True)
    except FileNotFoundError as e:
        return ToolResult(f"[FAIL] {e}", is_error=True)

    stdout = (proc.stdout or "")[:MAX_OUTPUT]
    stderr = (proc.stderr or "")[:MAX_OUTPUT]
    truncated = ""
    if proc.stdout and len(proc.stdout) > MAX_OUTPUT:
        truncated += f"\n[stdout truncated to {MAX_OUTPUT} bytes]"
    if proc.stderr and len(proc.stderr) > MAX_OUTPUT:
        truncated += f"\n[stderr truncated to {MAX_OUTPUT} bytes]"
    status = "OK" if proc.returncode == 0 else f"FAIL exit={proc.returncode}"
    body = f"[{status}] cwd={workdir}\n$ {command}\n"
    if stdout:
        body += f"--- stdout ---\n{stdout}\n"
    if stderr:
        body += f"--- stderr ---\n{stderr}\n"
    body += truncated
    return ToolResult(body, is_error=proc.returncode != 0)


TOOLS: list[Tool] = [
    Tool(
        name="shell_exec",
        description=(
            "Execute a shell command on the operator's local machine. "
            "Every command requires operator authorization, including informational commands. "
            "The CLI prompts interactively; the server checks its authorization gate. "
            "The confirm input is retained for compatibility and cannot bypass authorization."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run (sh/bash semantics)."},
                "cwd": {"type": "string", "description": "Optional working directory."},
                "timeout": {"type": "integer", "default": 60, "description": "Seconds before the command is killed."},
                "confirm": {"type": "boolean", "default": False, "description": "Legacy input; every command requires operator authorization regardless of this value."},
            },
            "required": ["command"],
        },
        run=_shell_exec,
        tags=["shell"],
    ),
]
