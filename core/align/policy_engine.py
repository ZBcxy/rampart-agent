"""Policy Engine Module

Defines and enforces operational policies for the Polaris agent.
Policies govern autonomy levels, resource usage limits, and operational boundaries.
"""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AutonomyLevel(Enum):
    """Agent autonomy levels."""

    L0_MANUAL = ("L0", "Fully manual — agent only suggests, never acts")
    L1_ASSISTED = ("L1", "Assisted — agent acts only after explicit user confirmation")
    L2_SUPERVISED = ("L2", "Supervised — agent acts autonomously but reports all actions")
    L3_AUTONOMOUS = ("L3", "Autonomous — agent acts freely within defined policy bounds")
    L4_FULL = ("L4", "Full autonomy — agent has complete decision-making authority")

    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description


@dataclass
class PolicyRule:
    """A single policy rule."""

    rule_id: str
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], Dict[str, Any]]
    priority: int = 0  # Higher priority rules evaluated first
    enabled: bool = True


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    reason: str
    matched_rules: List[str] = field(default_factory=list)
    modified_context: Dict[str, Any] = field(default_factory=dict)


class ResourceLimits:
    """Resource usage limits for agent operations."""

    def __init__(
        self,
        max_tokens_per_request: int = 16000,
        max_tokens_per_session: int = 200000,
        max_tool_calls_per_request: int = 50,
        max_step_count: int = 100,
        max_execution_time_seconds: float = 300.0,
        max_memory_items: int = 500,
        max_sandbox_count: int = 5,
    ):
        self.max_tokens_per_request = max_tokens_per_request
        self.max_tokens_per_session = max_tokens_per_session
        self.max_tool_calls_per_request = max_tool_calls_per_request
        self.max_step_count = max_step_count
        self.max_execution_time_seconds = max_execution_time_seconds
        self.max_memory_items = max_memory_items
        self.max_sandbox_count = max_sandbox_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_tokens_per_request": self.max_tokens_per_request,
            "max_tokens_per_session": self.max_tokens_per_session,
            "max_tool_calls_per_request": self.max_tool_calls_per_request,
            "max_step_count": self.max_step_count,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "max_memory_items": self.max_memory_items,
            "max_sandbox_count": self.max_sandbox_count,
        }


class PolicyEngine:
    """Policy engine that evaluates and enforces operational policies.

    Policies are evaluated as a chain — the first matching rule determines
    the decision. Rules are sorted by priority (higher first).
    """

    def __init__(self, autonomy_level: AutonomyLevel = AutonomyLevel.L2_SUPERVISED):
        """
        Initialize the policy engine.

        Args:
            autonomy_level: The agent's autonomy level
        """
        self.autonomy_level = autonomy_level
        self.resource_limits = ResourceLimits()
        self.rules: List[PolicyRule] = []
        self._session_stats: Dict[str, Any] = {
            "tokens_used": 0,
            "tool_calls_made": 0,
            "steps_executed": 0,
            "total_execution_time": 0.0,
        }
        self._lock = threading.Lock()
        self._register_default_rules()

    def _register_default_rules(self):
        """Register the default set of policy rules."""

        # Rule: Block destructive operations below L3
        self.add_rule(
            PolicyRule(
                rule_id="block_destructive_ops",
                name="Block Destructive Operations",
                description="Block file deletion, system modification below L3 autonomy",
                condition=lambda ctx: (
                    self.autonomy_level.value[0] in ("L0", "L1", "L2")
                    and ctx.get("operation_type") in ("delete", "remove", "destroy", "modify_system")
                ),
                action=lambda ctx: {
                    "allowed": False,
                    "reason": f"Destructive operation '{ctx.get('operation_type')}' blocked at autonomy level {self.autonomy_level.label}",
                },
                priority=100,
            )
        )

        # Rule: Require confirmation at L1
        self.add_rule(
            PolicyRule(
                rule_id="require_confirmation_l1",
                name="Require User Confirmation",
                description="Require explicit user confirmation at L1 autonomy",
                condition=lambda ctx: (
                    self.autonomy_level == AutonomyLevel.L1_ASSISTED
                    and not ctx.get("user_confirmed", False)
                    and ctx.get("operation_type") not in ("read", "query", "list")
                ),
                action=lambda ctx: {
                    "allowed": False,
                    "reason": "User confirmation required at L1 autonomy level",
                },
                priority=90,
            )
        )

        # Rule: Enforce token limits
        self.add_rule(
            PolicyRule(
                rule_id="enforce_token_limit",
                name="Enforce Token Limits",
                description="Block requests exceeding token limits",
                condition=lambda ctx: (
                    ctx.get("estimated_tokens", 0) > self.resource_limits.max_tokens_per_request
                ),
                action=lambda ctx: {
                    "allowed": False,
                    "reason": f"Request exceeds token limit ({self.resource_limits.max_tokens_per_request})",
                },
                priority=80,
            )
        )

        # Rule: Enforce step count limits
        self.add_rule(
            PolicyRule(
                rule_id="enforce_step_limit",
                name="Enforce Step Limit",
                description="Block when step count exceeds limit",
                condition=lambda ctx: (
                    self._session_stats["steps_executed"] >= self.resource_limits.max_step_count
                ),
                action=lambda ctx: {
                    "allowed": False,
                    "reason": f"Step count limit reached ({self.resource_limits.max_step_count})",
                },
                priority=80,
            )
        )

        # Rule: Allow all read operations
        self.add_rule(
            PolicyRule(
                rule_id="allow_read_ops",
                name="Allow Read Operations",
                description="Always allow read-only operations",
                condition=lambda ctx: ctx.get("operation_type") in ("read", "query", "list", "search"),
                action=lambda ctx: {"allowed": True, "reason": "Read operation always allowed"},
                priority=50,
            )
        )

        # Rule: Default allow at L3+
        self.add_rule(
            PolicyRule(
                rule_id="default_allow_l3",
                name="Default Allow at High Autonomy",
                description="Allow operations by default at L3+ autonomy",
                condition=lambda ctx: self.autonomy_level.value[0] in ("L3", "L4"),
                action=lambda ctx: {"allowed": True, "reason": f"Allowed at autonomy level {self.autonomy_level.label}"},
                priority=10,
            )
        )

    def add_rule(self, rule: PolicyRule):
        """Add a policy rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a policy rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        """
        Evaluate all policy rules against the given context.

        Args:
            context: Operation context (operation_type, user_id, etc.)

        Returns:
            PolicyDecision with the evaluation result
        """
        if not self.rules:
            return PolicyDecision(allowed=True, reason="No rules configured")

        with self._lock:
            for rule in self.rules:
                if not rule.enabled:
                    continue

                try:
                    matches = rule.condition(context)
                    if matches:
                        result = rule.action(context)
                        return PolicyDecision(
                            allowed=result.get("allowed", False),
                            reason=result.get("reason", f"Matched rule: {rule.name}"),
                            matched_rules=[rule.rule_id],
                            modified_context=result.get("context", {}),
                        )
                except Exception as e:
                    # Rule evaluation failed — log and continue to next rule
                    continue

        # Default: allow if no rules matched
        return PolicyDecision(allowed=True, reason="No rules matched — default allow")

    def check_operation(self, operation_type: str, **kwargs) -> PolicyDecision:
        """
        Convenience method to check if an operation is allowed.

        Args:
            operation_type: Type of operation
            **kwargs: Additional context

        Returns:
            PolicyDecision
        """
        context = {"operation_type": operation_type, **kwargs}
        return self.evaluate(context)

    def record_action(self, tokens: int = 0, tool_calls: int = 0, steps: int = 0, execution_time: float = 0.0):
        """Record an action's resource usage for limit tracking."""
        with self._lock:
            self._session_stats["tokens_used"] += tokens
            self._session_stats["tool_calls_made"] += tool_calls
            self._session_stats["steps_executed"] += steps
            self._session_stats["total_execution_time"] += execution_time

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        with self._lock:
            return dict(self._session_stats)

    def reset_session(self):
        """Reset session statistics."""
        with self._lock:
            for key in self._session_stats:
                self._session_stats[key] = 0

    def set_autonomy_level(self, level: AutonomyLevel):
        """Change the autonomy level."""
        self.autonomy_level = level

    def set_resource_limits(self, **kwargs):
        """Update resource limits."""
        for key, value in kwargs.items():
            if hasattr(self.resource_limits, key):
                setattr(self.resource_limits, key, value)

    def get_policy_summary(self) -> Dict[str, Any]:
        """Get a summary of the current policy configuration."""
        return {
            "autonomy_level": self.autonomy_level.label,
            "autonomy_description": self.autonomy_level.description,
            "active_rules": len([r for r in self.rules if r.enabled]),
            "total_rules": len(self.rules),
            "resource_limits": self.resource_limits.to_dict(),
            "session_stats": self.get_session_stats(),
        }
