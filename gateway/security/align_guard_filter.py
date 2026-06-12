"""Alignment guard filter for gateway-layer input/output safety checks.

Thin wrapper around core.align.AlignGuard that provides a consistent
interface for the gateway to validate user inputs and agent outputs.
"""

from typing import Any, Dict, Optional

from core.align.align_guard import AlignGuard, GuardResult


class AlignGuardFilter:
    """Gateway-level alignment filter wrapping core AlignGuard.

    Provides check_input / check_output methods that delegate to the
    core guard while keeping gateway callers decoupled from the internal API.
    """

    def __init__(self, guard: Optional[AlignGuard] = None):
        self._guard = guard or AlignGuard(enabled=True)

    def check_input(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Validate user input before processing."""
        return self._guard.check_input(content, context)

    def check_output(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """Validate agent output before returning to user."""
        return self._guard.check_output(content, context)

    @property
    def enabled(self) -> bool:
        return self._guard.enabled
