"""Intervention Log — structured recording of human modifications.

Maps to the Harness paper's "干预记录" responsibility: record every
human intervention in the agent's decision trajectory for audit,
debugging, and trajectory replay.

Types of interventions:
- CONFIRM: Human approved a proposed action
- DENY: Human rejected a proposed action
- MODIFY: Human modified the agent's content
- OVERRIDE: Human overrode the agent's decision
- INJECT: Human injected new context or instruction
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InterventionType(str, Enum):
    """Type of human intervention in agent decision trajectory."""
    CONFIRM = "confirm"       # Human approved a proposed action
    DENY = "deny"             # Human rejected a proposed action
    MODIFY = "modify"         # Human modified the agent's content
    OVERRIDE = "override"     # Human overrode the agent's decision entirely
    INJECT = "inject"         # Human injected new context or instruction


class InterventionRecord(BaseModel):
    """A single human intervention recorded in the decision trajectory."""
    intervention_id: str = Field(default_factory=lambda: f"int-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: str = "execution"  # "planning" | "execution" | "review"
    intervention_type: InterventionType = InterventionType.CONFIRM
    original_content: Optional[str] = None
    modified_content: Optional[str] = None
    reason: Optional[str] = None
    affected_agent_id: str = "default"
    affected_step_id: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InterventionLog:
    """Structured recording of all human modifications to agent decision trajectories.

    Supports filtering, statistics, and full trajectory export with
    interventions interleaved alongside agent steps.
    """

    def __init__(self, max_records: int = 5000):
        self._records: List[InterventionRecord] = []
        self._max_records = max_records

    # ── Recording ─────────────────────────────────────────────────────────

    def record(self, intervention_type: InterventionType, original: Optional[str] = None,
               modified: Optional[str] = None, reason: Optional[str] = None,
               context: Optional[Dict] = None) -> str:
        """Record an intervention and return its ID.

        Args:
            intervention_type: Type of intervention
            original: Original content before intervention
            modified: Modified content after intervention (if applicable)
            reason: Human-provided rationale
            context: Additional metadata (tool_name, phase, step, etc.)

        Returns:
            The intervention_id of the new record
        """
        context = context or {}
        record = InterventionRecord(
            phase=context.get("phase", "execution"),
            intervention_type=intervention_type,
            original_content=original,
            modified_content=modified,
            reason=reason,
            affected_step_id=context.get("step_id"),
            trace_id=context.get("trace_id"),
            metadata=context,
        )
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]
        return record.intervention_id

    # ── Querying ──────────────────────────────────────────────────────────

    def get_by_task(self, task_id: str) -> List[InterventionRecord]:
        """Get all interventions for a specific task (matched by trace_id or metadata)."""
        return [
            r for r in self._records
            if r.trace_id == task_id or r.metadata.get("task_id") == task_id
        ]

    def get_by_type(self, intervention_type: InterventionType) -> List[InterventionRecord]:
        """Get all interventions of a specific type."""
        return [r for r in self._records if r.intervention_type == intervention_type]

    def get_by_phase(self, phase: str) -> List[InterventionRecord]:
        """Get all interventions in a specific phase."""
        return [r for r in self._records if r.phase == phase]

    def get_by_time_range(self, start: str, end: str) -> List[InterventionRecord]:
        """Get interventions within a time range (ISO format timestamps)."""
        return [
            r for r in self._records
            if start <= r.timestamp <= end
        ]

    def get_all(self, limit: int = 100, offset: int = 0) -> List[InterventionRecord]:
        """Get paginated list of all intervention records."""
        return self._records[offset:offset + limit]

    def get_recent(self, limit: int = 20) -> List[InterventionRecord]:
        """Get most recent interventions."""
        return self._records[-limit:]

    # ── Trajectory Export ─────────────────────────────────────────────────

    def export_trajectory(self, task_id: str = "") -> Dict[str, Any]:
        """Export full task trajectory with interventions interleaved.

        Returns a dict with all interventions, statistics, and timeline.
        """
        records = self.get_by_task(task_id) if task_id else self._records
        records_sorted = sorted(records, key=lambda r: r.timestamp)

        return {
            "task_id": task_id or "all",
            "total_interventions": len(records_sorted),
            "timeline": [
                {
                    "intervention_id": r.intervention_id,
                    "timestamp": r.timestamp,
                    "type": r.intervention_type.value,
                    "phase": r.phase,
                    "original": r.original_content,
                    "modified": r.modified_content,
                    "reason": r.reason,
                    "step": r.affected_step_id,
                }
                for r in records_sorted
            ],
            "statistics": self.get_statistics(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Statistics ────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Summary statistics of all recorded interventions."""
        total = len(self._records)
        if total == 0:
            return {"total_interventions": 0, "by_type": {}, "by_phase": {},
                    "approval_rate": 0.0, "modification_rate": 0.0}

        type_counts: Dict[str, int] = {}
        phase_counts: Dict[str, int] = {}
        for r in self._records:
            t = r.intervention_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            phase_counts[r.phase] = phase_counts.get(r.phase, 0) + 1

        confirms = type_counts.get("confirm", 0)
        denies = type_counts.get("deny", 0)
        total_approve = confirms + denies

        return {
            "total_interventions": total,
            "by_type": type_counts,
            "by_phase": phase_counts,
            "approval_rate": round(confirms / total_approve, 2) if total_approve > 0 else 0.0,
            "modification_rate": round(
                type_counts.get("modify", 0) + type_counts.get("override", 0),
            ) / max(total, 1),
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all intervention records."""
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)
