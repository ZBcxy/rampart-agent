"""Unit tests for the Intervention Log module."""

import pytest
import json
from core.intervention import InterventionLog, InterventionRecord, InterventionType


class TestInterventionRecord:
    def test_record_default_fields(self):
        record = InterventionRecord(
            intervention_type=InterventionType.CONFIRM,
            phase="execution",
        )
        assert record.intervention_id.startswith("int-")
        assert record.intervention_type == InterventionType.CONFIRM
        assert record.phase == "execution"
        assert len(record.timestamp) > 0
        assert record.original_content is None

    def test_record_all_fields(self):
        record = InterventionRecord(
            phase="planning",
            intervention_type=InterventionType.MODIFY,
            original_content='{"action": "delete_file"}',
            modified_content='{"action": "read_file"}',
            reason="Deletion too risky, changed to read",
            affected_agent_id="agent-1",
            affected_step_id="step-3",
            trace_id="trace-abc",
            metadata={"task_id": "task-1"},
        )
        assert record.intervention_type == InterventionType.MODIFY
        assert "delete_file" in (record.original_content or "")
        assert "read_file" in (record.modified_content or "")
        assert record.affected_step_id == "step-3"
        assert record.trace_id == "trace-abc"

    def test_record_serialization(self):
        record = InterventionRecord(
            phase="review",
            intervention_type=InterventionType.OVERRIDE,
            reason="Safety concern",
        )
        d = record.model_dump()
        assert d["phase"] == "review"
        assert d["intervention_type"] == "override"


class TestInterventionLog:
    def test_record_confirm(self):
        log = InterventionLog()
        rid = log.record(
            intervention_type=InterventionType.CONFIRM,
            original='{"tool": "shell_exec", "args": {}}',
            reason="User approved",
            context={"tool_name": "shell_exec", "phase": "execution"},
        )
        assert rid.startswith("int-")
        assert len(log) == 1

    def test_record_deny(self):
        log = InterventionLog()
        log.record(
            intervention_type=InterventionType.DENY,
            original='{"tool": "file_delete", "args": {"path": "/tmp/test"}}',
            reason="User denied deletion",
            context={"tool_name": "file_delete"},
        )
        records = log.get_by_type(InterventionType.DENY)
        assert len(records) == 1
        assert records[0].intervention_type == InterventionType.DENY

    def test_record_modify(self):
        log = InterventionLog()
        log.record(
            intervention_type=InterventionType.MODIFY,
            original='{"content": "bad output"}',
            modified='{"content": "good output"}',
            reason="Corrected agent output",
            context={"phase": "review"},
        )
        assert len(log) == 1
        assert "bad output" in (log.get_recent(1)[0].original_content or "")

    def test_get_by_type(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM, "a")
        log.record(InterventionType.DENY, "b")
        log.record(InterventionType.CONFIRM, "c")

        confirms = log.get_by_type(InterventionType.CONFIRM)
        denies = log.get_by_type(InterventionType.DENY)
        assert len(confirms) == 2
        assert len(denies) == 1

    def test_get_by_phase(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM, context={"phase": "planning"})
        log.record(InterventionType.CONFIRM, context={"phase": "execution"})
        log.record(InterventionType.DENY, context={"phase": "execution"})

        planning = log.get_by_phase("planning")
        execution = log.get_by_phase("execution")
        assert len(planning) == 1
        assert len(execution) == 2

    def test_get_by_time_range(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM)
        # Query a wide range that should include the record
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        records = log.get_by_time_range(past, now)
        assert len(records) >= 1

    def test_export_trajectory(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM, original="test",
                   context={"task_id": "task-1", "trace_id": "task-1"})
        log.record(InterventionType.INJECT, modified='{"key": "value"}',
                   reason="Added context", context={"task_id": "task-1", "trace_id": "task-1"})

        trajectory = log.export_trajectory("task-1")
        assert trajectory["total_interventions"] == 2
        assert len(trajectory["timeline"]) == 2
        assert "statistics" in trajectory
        assert "exported_at" in trajectory

    def test_statistics(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM)
        log.record(InterventionType.CONFIRM)
        log.record(InterventionType.DENY)

        stats = log.get_statistics()
        assert stats["total_interventions"] == 3
        assert stats["by_type"]["confirm"] == 2
        assert stats["by_type"]["deny"] == 1
        assert stats["approval_rate"] > 0.5  # 2/3

    def test_pagination(self):
        log = InterventionLog()
        for i in range(5):
            log.record(InterventionType.CONFIRM, f"item-{i}")

        page1 = log.get_all(limit=2, offset=0)
        page2 = log.get_all(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2

    def test_clear(self):
        log = InterventionLog()
        log.record(InterventionType.CONFIRM)
        assert len(log) == 1
        log.clear()
        assert len(log) == 0
        assert log.get_statistics()["total_interventions"] == 0

    def test_max_records_limit(self):
        log = InterventionLog(max_records=5)
        for i in range(10):
            log.record(InterventionType.CONFIRM, original=f"item-{i}")
        assert len(log) == 5
        # Should keep most recent
        assert "item-9" in (log.get_recent(1)[0].original_content or "")


class TestInterventionType:
    def test_all_enum_values(self):
        assert InterventionType.CONFIRM.value == "confirm"
        assert InterventionType.DENY.value == "deny"
        assert InterventionType.MODIFY.value == "modify"
        assert InterventionType.OVERRIDE.value == "override"
        assert InterventionType.INJECT.value == "inject"

    def test_enum_from_string(self):
        assert InterventionType("confirm") == InterventionType.CONFIRM
        assert InterventionType("deny") == InterventionType.DENY
