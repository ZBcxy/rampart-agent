"""Tests for the retry-aware DAG executor."""

import asyncio

import pytest
from core.executor.retry_executor import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    RetryConfig,
    RetryableDAGExecutor,
)


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_failures(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)

        def failing():
            raise ValueError("fail")

        for _ in range(3):
            try:
                cb.call(failing)
            except ValueError:
                pass

        assert cb.state == CircuitState.OPEN

    def test_successful_calls_keep_closed(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)

        def success():
            return "ok"

        for _ in range(10):
            result = cb.call(success)
            assert result == "ok"

        assert cb.state == CircuitState.CLOSED

    def test_raises_when_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=9999)

        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not run")

    def test_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)

        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED


class TestRetryConfig:
    def test_default_values(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0

    def test_exponential_backoff(self):
        """Test exponential backoff base formula (without jitter)."""
        executor = RetryableDAGExecutor()
        # Disable jitter for deterministic testing
        executor.retry_config.jitter = False

        delay_0 = executor._calculate_backoff(0)
        delay_1 = executor._calculate_backoff(1)
        delay_2 = executor._calculate_backoff(2)

        # Without jitter: base * exponent^attempt
        assert delay_0 == pytest.approx(1.0)  # 1.0 * 2^0
        assert delay_1 == pytest.approx(2.0)  # 1.0 * 2^1
        assert delay_2 == pytest.approx(4.0)  # 1.0 * 2^2
        assert delay_0 < delay_1 < delay_2
        assert delay_2 <= executor.retry_config.max_delay


class TestRetryableDAGExecutor:
    @pytest.fixture
    def executor(self):
        return RetryableDAGExecutor()

    def test_simple_dag_execution(self, executor):
        dag = {
            "nodes": [
                {"id": "n0", "type": "action", "content": "step 1", "confidence": 0.9},
                {"id": "n1", "type": "action", "content": "step 2", "confidence": 0.8},
            ],
            "edges": [{"from": "n0", "to": "n1"}],
        }
        context = {"input_data": {}}

        results = asyncio.run(executor.execute_dag(dag, context))

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_circuit_breaker_integration(self, executor):
        cb = executor.get_circuit_breaker("tool_test")
        assert cb.name == "tool_test"
        assert cb.state == CircuitState.CLOSED

    def test_dead_letter_queue(self, executor):
        assert len(executor.get_dead_letter_queue()) == 0
        executor.clear_all()
        assert len(executor.get_dead_letter_queue()) == 0
