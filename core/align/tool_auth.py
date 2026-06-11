"""Tool Authorization & Human-in-the-Loop

Per-tool access control, audit logging, and confirmation flows for L1/L2 autonomy.

Usage:
    from core.align.tool_auth import ToolAuthorizer, ConfirmationHandler

    auth = ToolAuthorizer()
    auth.grant("admin", "shell_exec")
    auth.grant("user", "file_read")

    if auth.authorize("user", "shell_exec"):
        # allowed
    else:
        # requires elevation or confirmation

    # Human-in-the-loop
    handler = ConfirmationHandler(callback=my_ui_prompt_function)
    approved = await handler.request_confirmation("shell_exec", {"command": "rm file.txt"})
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from core.align.policy_engine import AutonomyLevel


class ToolCategory(str, Enum):
    SAFE = "safe"           # Read-only, no side effects
    MODIFY = "modify"       # Writes/modifies data
    DANGEROUS = "dangerous" # System access, deletion, execution


@dataclass
class ToolPolicy:
    """Access policy for a tool."""
    tool_name: str
    category: ToolCategory
    min_autonomy: AutonomyLevel = AutonomyLevel.L1_ASSISTED
    require_confirmation: bool = True
    max_per_session: int = 100
    max_per_minute: int = 10
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "operator"])


@dataclass
class AuditEntry:
    """Audit log entry for tool execution."""
    timestamp: str
    user: str
    tool: str
    arguments: Dict[str, Any]
    authorized: bool
    confirmed: bool
    result: str  # "success" | "error" | "denied"


# Default tool policies
DEFAULT_POLICIES = {
    # File tools
    "file_read": ToolPolicy("file_read", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "file_write": ToolPolicy("file_write", ToolCategory.MODIFY, AutonomyLevel.L1_ASSISTED, True),
    "file_delete": ToolPolicy("file_delete", ToolCategory.DANGEROUS, AutonomyLevel.L0_MANUAL, True, max_per_session=10, max_per_minute=2),
    "file_list": ToolPolicy("file_list", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "file_search": ToolPolicy("file_search", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "file_info": ToolPolicy("file_info", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "file_move": ToolPolicy("file_move", ToolCategory.MODIFY, AutonomyLevel.L1_ASSISTED, True),
    "file_copy": ToolPolicy("file_copy", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False),
    "file_mkdir": ToolPolicy("file_mkdir", ToolCategory.MODIFY, AutonomyLevel.L2_SUPERVISED, False),
    # Web tools
    "web_search": ToolPolicy("web_search", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "web_fetch": ToolPolicy("web_fetch", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "http_request": ToolPolicy("http_request", ToolCategory.MODIFY, AutonomyLevel.L1_ASSISTED, True),
    "url_encode": ToolPolicy("url_encode", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    # Code tools
    "python_exec": ToolPolicy("python_exec", ToolCategory.DANGEROUS, AutonomyLevel.L1_ASSISTED, True, max_per_session=50),
    "code_analyze": ToolPolicy("code_analyze", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "json_format": ToolPolicy("json_format", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "regex_test": ToolPolicy("regex_test", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    # Data tools
    "text_process": ToolPolicy("text_process", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "csv_parse": ToolPolicy("csv_parse", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "calc": ToolPolicy("calc", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "data_transform": ToolPolicy("data_transform", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    # System tools
    "system_info": ToolPolicy("system_info", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "shell_exec": ToolPolicy("shell_exec", ToolCategory.DANGEROUS, AutonomyLevel.L0_MANUAL, True, max_per_session=5, max_per_minute=1),
    "env_var": ToolPolicy("env_var", ToolCategory.SAFE, AutonomyLevel.L1_ASSISTED, False),
    "time_now": ToolPolicy("time_now", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
    "disk_usage": ToolPolicy("disk_usage", ToolCategory.SAFE, AutonomyLevel.L2_SUPERVISED, False, allowed_roles=["*"]),
}


class ToolAuthorizer:
    """Per-tool access control with role-based permissions.

    Integrates with PolicyEngine for autonomy-level gating.
    """

    def __init__(self):
        self._policies: Dict[str, ToolPolicy] = dict(DEFAULT_POLICIES)
        self._role_permissions: Dict[str, Set[str]] = {}  # role -> {tool_names}
        self._audit_log: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._session_counts: Dict[str, int] = {}  # tool -> count
        self._minute_counts: Dict[str, List[float]] = {}  # tool -> [timestamps]

        # Default role grants
        self._role_permissions["admin"] = set(self._policies.keys())
        self._role_permissions["operator"] = {
            t for t, p in self._policies.items()
            if p.category != ToolCategory.DANGEROUS
        }
        self._role_permissions["user"] = {
            t for t, p in self._policies.items()
            if p.category == ToolCategory.SAFE
        }

    def authorize(
        self,
        role: str,
        tool_name: str,
        autonomy_level: AutonomyLevel = AutonomyLevel.L2_SUPERVISED,
    ) -> Dict[str, Any]:
        """Check if a role can use a tool.

        Returns:
            {"allowed": bool, "reason": str, "requires_confirmation": bool}
        """
        policy = self._policies.get(tool_name)
        if not policy:
            return {"allowed": False, "reason": f"Unknown tool: {tool_name}", "requires_confirmation": False}

        # Role check
        allowed_roles = policy.allowed_roles
        if "*" not in allowed_roles and role not in allowed_roles:
            has_permission = tool_name in self._role_permissions.get(role, set())
            if not has_permission:
                return {"allowed": False, "reason": f"Role '{role}' not authorized for '{tool_name}'", "requires_confirmation": False}

        # Autonomy check
        autonomy_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
        if autonomy_order.get(autonomy_level.value[0] + autonomy_level.value[1], 0) < autonomy_order.get(policy.min_autonomy.value[0] + policy.min_autonomy.value[1], 0):
            return {
                "allowed": False,
                "reason": f"'{tool_name}' requires {policy.min_autonomy.label}, current: {autonomy_level.label}",
                "requires_confirmation": True,
            }

        # Rate limit check
        if not self._check_rate_limit(tool_name):
            return {"allowed": False, "reason": f"Rate limit exceeded for '{tool_name}'", "requires_confirmation": False}

        return {
            "allowed": True,
            "reason": "Authorized",
            "requires_confirmation": policy.require_confirmation,
        }

    def grant(self, role: str, tool_name: str):
        """Grant a role access to a specific tool."""
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].add(tool_name)

    def revoke(self, role: str, tool_name: str):
        """Revoke a role's access to a tool."""
        if role in self._role_permissions:
            self._role_permissions[role].discard(tool_name)

    def record_execution(self, user: str, tool: str, arguments: Dict, authorized: bool, confirmed: bool, success: bool):
        """Record a tool execution in the audit log."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            user=user,
            tool=tool,
            arguments=arguments,
            authorized=authorized,
            confirmed=confirmed,
            result="success" if success else "error" if authorized else "denied",
        )
        with self._lock:
            self._audit_log.append(entry)
            self._session_counts[tool] = self._session_counts.get(tool, 0) + 1

            import time
            now = time.time()
            if tool not in self._minute_counts:
                self._minute_counts[tool] = []
            self._minute_counts[tool].append(now)
            # Trim old entries
            self._minute_counts[tool] = [t for t in self._minute_counts[tool] if now - t < 60]

    def _check_rate_limit(self, tool_name: str) -> bool:
        policy = self._policies.get(tool_name)
        if not policy:
            return True

        session_count = self._session_counts.get(tool_name, 0)
        if session_count >= policy.max_per_session:
            return False

        import time
        now = time.time()
        minute_count = sum(1 for t in self._minute_counts.get(tool_name, []) if now - t < 60)
        if minute_count >= policy.max_per_minute:
            return False

        return True

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        return [vars(e) for e in self._audit_log[-limit:]]

    def get_policy(self, tool_name: str) -> Optional[Dict]:
        p = self._policies.get(tool_name)
        return vars(p) if p else None


class ConfirmationHandler:
    """Human-in-the-loop confirmation for tool execution.

    At L1 (Assisted) autonomy, dangerous tool calls pause and wait
    for explicit user confirmation via a pluggable callback.

    Usage:
        handler = ConfirmationHandler(callback=my_ui_prompt)
        result = await handler.request("shell_exec", {"command": "rm -rf /tmp/test"})
        if result.approved:
            execute()
    """

    def __init__(self, callback: Optional[Callable[[str, Dict], bool]] = None, timeout: float = 300.0):
        """
        Args:
            callback: Function(tool_name, arguments) -> bool for user confirmation
            timeout: Max seconds to wait for confirmation
        """
        self.callback = callback
        self.timeout = timeout
        self._pending: Dict[str, Any] = {}

    async def request_confirmation(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Request user confirmation for a tool call.

        Returns:
            True if user approved, False if denied or timed out
        """
        import asyncio

        if not self.callback:
            return False

        # Build confirmation message
        msg = self._format_message(tool_name, arguments)

        try:
            if asyncio.iscoroutinefunction(self.callback):
                approved = await asyncio.wait_for(
                    self.callback(tool_name, arguments),
                    timeout=self.timeout,
                )
            else:
                approved = self.callback(tool_name, arguments)
            return bool(approved)
        except asyncio.TimeoutError:
            return False
        except Exception:
            return False

    def request_confirmation_sync(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Synchronous confirmation request."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running event loop, use a future
                future = asyncio.ensure_future(
                    self.request_confirmation(tool_name, arguments)
                )
                return future.result(timeout=self.timeout)
            return loop.run_until_complete(
                self.request_confirmation(tool_name, arguments)
            )
        except Exception:
            return False

    def _format_message(self, tool_name: str, arguments: Dict) -> str:
        """Format a human-readable confirmation message."""
        args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
        return f"⚠️  [{tool_name}] with: {args_str}\nApprove this action? (y/n)"
