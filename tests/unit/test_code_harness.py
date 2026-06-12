"""Unit tests for the Code Harness module."""

import pytest
from core.executor.code_harness import (
    ActionCodeValidator,
    CodeHarness,
    HarnessTraceItem,
    ValidationResult,
)


class TestActionCodeValidator:
    def test_valid_simple_expression(self):
        validator = ActionCodeValidator()
        result = validator.validate("result = sum([1, 2, 3])")
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_function_call(self):
        validator = ActionCodeValidator()
        result = validator.validate("len('hello')")
        assert result.is_valid

    def test_valid_import(self):
        validator = ActionCodeValidator()
        result = validator.validate("import math\nresult = math.sqrt(16)")
        assert result.is_valid

    def test_syntax_error(self):
        validator = ActionCodeValidator()
        result = validator.validate("this is %% not valid python @@@")
        assert not result.is_valid
        assert any("Syntax" in e for e in result.errors)

    def test_empty_code(self):
        validator = ActionCodeValidator()
        result = validator.validate("")
        assert not result.is_valid
        assert any("Empty" in e for e in result.errors)

    def test_side_effect_detection_write(self):
        validator = ActionCodeValidator()
        result = validator.validate("open('/tmp/test.txt', 'w')")
        # open() is detected as a side effect
        assert len(result.side_effects) > 0

    def test_disallowed_import(self):
        validator = ActionCodeValidator()
        result = validator.validate("import os\nos.system('ls')")
        # os is not in ALLOWED_IMPORTS
        assert not result.is_valid

    def test_disallowed_import_from(self):
        validator = ActionCodeValidator()
        result = validator.validate("from subprocess import run")
        assert not result.is_valid


class TestCodeHarness:
    def test_execute_action_code_valid(self):
        harness = CodeHarness()
        result = harness.execute_action_code("result = 1 + 2 * 3")
        assert result["validated"]
        # Execution may or may not succeed depending on sandbox state
        assert "execution_time" in result

    def test_execute_action_code_invalid(self):
        harness = CodeHarness()
        result = harness.execute_action_code("import os\nos.system('rm -rf /')")
        assert not result["validated"]
        assert len(result.get("error", "")) > 0

    def test_execute_action_code_empty(self):
        harness = CodeHarness()
        result = harness.execute_action_code("")
        assert not result["validated"]

    def test_execute_action_code_async_valid(self):
        import asyncio
        harness = CodeHarness()

        async def run():
            return await harness.execute_action_code_async("result = 42")

        result = asyncio.run(run())
        assert result["validated"]
        assert "execution_time" in result

    def test_execute_action_code_async_invalid(self):
        import asyncio
        harness = CodeHarness()

        async def run():
            return await harness.execute_action_code_async("import os\nos.system('ls')")

        result = asyncio.run(run())
        assert not result["validated"]

    def test_trace_recording(self):
        harness = CodeHarness()
        harness.execute_action_code("a = 1")
        harness.execute_action_code("b = a + 1")
        trace = harness.get_trace()
        assert len(trace) == 2
        assert trace[0].step_index == 1
        assert trace[1].step_index == 2

    def test_trace_summary(self):
        harness = CodeHarness()
        harness.execute_action_code("x = 1")
        summary = harness.get_trace_summary()
        assert summary["total_executions"] >= 1
        assert "success_rate" in summary
        assert "avg_execution_time" in summary

    def test_reset_sandbox(self):
        harness = CodeHarness()
        harness.execute_action_code("a = 1")
        harness.reset_sandbox()
        # After reset, should still be able to execute
        result = harness.execute_action_code("b = 2")
        assert result["validated"]

    def test_shutdown(self):
        harness = CodeHarness()
        harness.execute_action_code("a = 1")
        harness.shutdown()
        # After shutdown, trace should still be accessible
        assert len(harness.get_trace()) >= 1


class TestHarnessTraceItem:
    def test_trace_item_defaults(self):
        item = HarnessTraceItem(code="x = 1")
        assert item.code == "x = 1"
        assert not item.validated
        assert item.step_index == 0
        assert len(item.timestamp) > 0

    def test_trace_item_full(self):
        item = HarnessTraceItem(
            step_index=3,
            code="result = sum([1,2])",
            validated=True,
            execution_result={"success": True, "result": "3"},
            execution_time=0.05,
            side_effects=[],
            error=None,
        )
        assert item.step_index == 3
        assert item.validated
        assert item.execution_time == 0.05
        assert item.execution_result and item.execution_result["success"]


class TestValidationResult:
    def test_valid_result(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert result.errors == []
        assert result.side_effects == []

    def test_invalid_result(self):
        result = ValidationResult(
            is_valid=False,
            errors=["Syntax error", "Disallowed import"],
            side_effects=["Side effect: open() call"],
        )
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.side_effects) == 1
