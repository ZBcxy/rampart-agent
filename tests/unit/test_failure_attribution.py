"""Unit tests for the Failure Attribution module."""

import pytest
from core.failure_attribution import (
    FailureCategory,
    FailureClassifier,
    FailureEvidence,
    FailureReport,
)
from core.exceptions import (
    ConfigurationMissingError,
    ToolExecutionError,
    PlanGenerationError,
    TimeoutException,
)


class TestFailureClassifier:
    def test_classify_llm_reasoning_json_parse_error(self):
        classifier = FailureClassifier()
        error = ValueError("JSON parse error: unexpected token")
        report = classifier.classify(error, {"phase": "decide"})
        assert report.category == FailureCategory.LLM_REASONING
        assert report.confidence > 0.1
        assert len(report.evidence) > 0

    def test_classify_llm_reasoning_plan_error(self):
        classifier = FailureClassifier()
        error = PlanGenerationError("plan is malformed and incomplete")
        report = classifier.classify(error, {"phase": "planning"})
        assert report.category == FailureCategory.LLM_REASONING
        assert "simplifying the prompt" in report.suggested_fix.lower()

    def test_classify_tool_execution_timeout(self):
        classifier = FailureClassifier()
        error = TimeoutException("Operation timed out after 30 seconds", 30.0)
        report = classifier.classify(error, {"tool_name": "web_fetch"})
        assert report.category in (FailureCategory.TOOL_EXECUTION, FailureCategory.UNKNOWN)

    def test_classify_tool_execution_permission(self):
        classifier = FailureClassifier()
        error = PermissionError("access denied for file_write")
        report = classifier.classify(error, {"tool_name": "file_write"})
        # PermissionError message matches TOOL_PATTERNS (permission)
        assert len(report.evidence) > 0

    def test_classify_harness_defect_circuit_breaker(self):
        classifier = FailureClassifier()
        error = RuntimeError("circuit breaker open: too many failures")
        report = classifier.classify(error, {"phase": "execution"})
        assert report.category == FailureCategory.HARNESS_DEFECT

    def test_classify_harness_defect_config(self):
        classifier = FailureClassifier()
        error = ConfigurationMissingError("Missing config", "API_KEY")
        report = classifier.classify(error)
        assert report.category == FailureCategory.HARNESS_DEFECT

    def test_classify_external_api_error(self):
        classifier = FailureClassifier()
        error = ConnectionError("API returned HTTP 500: provider unavailable")
        report = classifier.classify(error, {"phase": "llm_call"})
        assert report.category in (FailureCategory.EXTERNAL, FailureCategory.UNKNOWN)

    def test_classify_unknown_fallback(self):
        classifier = FailureClassifier()
        error = RuntimeError("xyzzy_unknown_error_abc123")
        report = classifier.classify(error)
        assert isinstance(report.category, FailureCategory)
        assert report.category in (FailureCategory.UNKNOWN, FailureCategory.TOOL_EXECUTION,
                                    FailureCategory.HARNESS_DEFECT, FailureCategory.EXTERNAL)

    def test_classify_with_tool_execution_error_type(self):
        classifier = FailureClassifier()
        error = ToolExecutionError("tool abc failed", tool_id="abc")
        report = classifier.classify(error)
        assert report.category == FailureCategory.TOOL_EXECUTION
        assert report.confidence > 0.5

    def test_failure_statistics_aggregation(self):
        classifier = FailureClassifier()
        classifier.classify(ValueError("JSON parse error"), {"phase": "decide"})
        classifier.classify(PermissionError("access denied"), {"phase": "act"})
        classifier.classify(RuntimeError("circuit breaker open"), {"phase": "execute"})

        stats = classifier.get_failure_statistics()
        assert stats["total_failures"] == 3
        assert len(stats["categories"]) > 0
        assert 0 < stats["avg_confidence"] <= 1.0

    def test_recent_failures(self):
        classifier = FailureClassifier(history_limit=5)
        for i in range(7):
            classifier.classify(ValueError(f"error {i}"))
        assert len(classifier.get_recent_failures(10)) == 5  # capped at history_limit

    def test_clear(self):
        classifier = FailureClassifier()
        classifier.classify(ValueError("test error"))
        assert classifier.get_failure_statistics()["total_failures"] == 1
        classifier.clear()
        assert classifier.get_failure_statistics()["total_failures"] == 0


class TestFailureReport:
    def test_report_default_fields(self):
        report = FailureReport(
            error_type="ValueError",
            error_message="Something went wrong",
        )
        assert report.category == FailureCategory.UNKNOWN
        assert report.confidence == 0.0
        assert report.failure_id.startswith("fail-")
        assert len(report.timestamp) > 0
        # suggested_fix is populated by FailureClassifier.classify(), not on direct construction
        assert isinstance(report.suggested_fix, str)

    def test_report_full_serialization(self):
        evidence = FailureEvidence(source="exception_type", detail="Test detail")
        report = FailureReport(
            category=FailureCategory.TOOL_EXECUTION,
            confidence=0.85,
            evidence=[evidence],
            error_type="ToolExecutionError",
            error_message="Tool failed",
            suggested_fix="Check tool parameters",
        )
        d = report.model_dump()
        assert d["category"] == "tool_execution"
        assert d["confidence"] == 0.85
        assert len(d["evidence"]) == 1


class TestFailureEvidence:
    def test_evidence_default_weight(self):
        ev = FailureEvidence(source="pattern_match", detail="matched timeout pattern")
        assert ev.weight == 1.0

    def test_evidence_custom_weight(self):
        ev = FailureEvidence(source="stack_trace", detail="originated in executor", weight=0.5)
        assert ev.weight == 0.5

    def test_evidence_weight_bounds(self):
        ev = FailureEvidence(source="error_message", detail="test", weight=0.0)
        assert ev.weight >= 0.0
        ev2 = FailureEvidence(source="error_message", detail="test", weight=1.0)
        assert ev2.weight <= 1.0
