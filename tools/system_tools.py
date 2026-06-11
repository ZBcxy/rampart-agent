"""System Tools - Monitoring, process management, environment info."""

import os
import platform
import subprocess
from datetime import datetime
from typing import Any, Dict

from tools.registry import ToolDefinition, ToolRegistry


def register_system_tools(registry: ToolRegistry):
    """Register all system utility tools."""
    registry.register_many([
        ToolDefinition(
            name="system_info",
            description="Get system information: OS, CPU, memory, disk, Python version.",
            func=_system_info,
            parameters={},
            category="system",
            tags=["system", "info", "monitoring"],
        ),
        ToolDefinition(
            name="shell_exec",
            description="Execute a shell command and return stdout/stderr.",
            func=_shell_exec,
            parameters={
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                "working_dir": {"type": "string", "description": "Working directory"},
            },
            category="system",
            requires_confirmation=True,
            tags=["shell", "command", "execution"],
        ),
        ToolDefinition(
            name="env_var",
            description="Read or set environment variables.",
            func=_env_var,
            parameters={
                "name": {"type": "string", "description": "Variable name"},
                "value": {"type": "string", "description": "Value to set (omit to read)"},
            },
            category="system",
            tags=["env", "config", "system"],
        ),
        ToolDefinition(
            name="time_now",
            description="Get current date, time, and timezone information.",
            func=_time_now,
            parameters={
                "timezone": {"type": "string", "description": "Timezone name (e.g., 'Asia/Shanghai', 'UTC')"},
                "format": {"type": "string", "description": "strftime format string"},
            },
            category="system",
            tags=["time", "date", "utility"],
        ),
        ToolDefinition(
            name="disk_usage",
            description="Get disk usage information for a path.",
            func=_disk_usage,
            parameters={
                "path": {"type": "string", "description": "Path to check (default: current directory)"},
            },
            category="system",
            tags=["disk", "storage", "monitoring"],
        ),
    ])


def _system_info() -> Dict[str, Any]:
    """Get comprehensive system information."""
    import sys

    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "hostname": platform.node(),
        "current_time": datetime.now().isoformat(),
        "current_directory": os.getcwd(),
        "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
    }

    # CPU count
    try:
        info["cpu_count"] = os.cpu_count()
    except Exception:
        info["cpu_count"] = "unknown"

    # Memory (Linux)
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    info["memory_total_kb"] = int(line.split()[1])
                elif "MemAvailable" in line:
                    info["memory_available_kb"] = int(line.split()[1])
                    break
    except Exception:
        pass

    return info


def _shell_exec(command: str, timeout: int = 30, working_dir: str = None) -> Dict[str, Any]:
    """Execute a shell command."""

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir or os.getcwd(),
        )

        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout[:10000] if result.stdout else "",
            "stderr": result.stderr[:5000] if result.stderr else "",
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}


def _env_var(name: str, value: str = None) -> Dict[str, Any]:
    """Read or set environment variable."""
    if value is not None:
        os.environ[name] = value
        return {"name": name, "action": "set", "value": value}
    else:
        val = os.environ.get(name, None)
        return {"name": name, "action": "read", "value": val, "exists": val is not None}


def _time_now(timezone: str = None, format: str = None) -> Dict[str, Any]:
    """Get current time information."""
    now = datetime.now()

    result = {
        "iso": now.isoformat(),
        "unix_timestamp": now.timestamp(),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "weekday": now.strftime("%A"),
        "timezone": timezone or "local",
    }

    if timezone:
        try:
            import zoneinfo
            tz_info = zoneinfo.ZoneInfo(timezone)
            now_tz = datetime.now(tz_info)
            result["iso"] = now_tz.isoformat()
            result["hour"] = now_tz.hour
            result["minute"] = now_tz.minute
        except Exception:
            pass

    if format:
        result["formatted"] = now.strftime(format)

    return result


def _disk_usage(path: str = None) -> Dict[str, Any]:
    """Get disk usage."""
    import shutil

    path = path or os.getcwd()
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "usage_percent": round(usage.used / usage.total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e), "path": path}
