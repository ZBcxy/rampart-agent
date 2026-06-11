"""Retry-Aware DAG Executor

Extends the DAG executor with retry logic, circuit breaker pattern,
exponential backoff, and comprehensive error recovery.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from .dag_executor import DAGExecutor, ExecutionResult


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for a specific tool/node."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_requests: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    half_open_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If the circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_requests = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_requests >= self.half_open_max_requests:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is HALF_OPEN at max requests")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async version of circuit breaker call."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_requests = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_requests >= self.half_open_max_requests:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is HALF_OPEN at max requests")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.total_successes += 1
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_requests += 1
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN and self.half_open_requests >= self.half_open_max_requests:
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def reset(self):
        """Reset the circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_requests = 0


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is open and rejecting requests."""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[type, ...] = (TimeoutError, ConnectionError, CircuitBreakerOpenError)


class RetryableDAGExecutor(DAGExecutor):
    """DAG executor with retry logic and circuit breakers.

    Extends the base DAGExecutor with:
    - Exponential backoff retry for failed nodes
    - Circuit breaker pattern to prevent cascading failures
    - Dead letter queue for persistently failing nodes
    - Comprehensive execution statistics
    """

    def __init__(self, sandbox_manager=None, retry_config: Optional[RetryConfig] = None):
        super().__init__(sandbox_manager)
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self._node_retry_counts: Dict[str, int] = defaultdict(int)
        self._execution_times: Dict[str, List[float]] = defaultdict(list)

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a node/tool."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name=name)
        return self.circuit_breakers[name]

    async def execute_dag(
        self,
        dag: Dict[str, Any],
        context: Dict[str, Any],
        retry_on_failure: bool = True,
    ) -> List[ExecutionResult]:
        """
        Execute DAG with retry support.

        Args:
            dag: DAG structure
            context: Execution context
            retry_on_failure: Whether to retry failed nodes

        Returns:
            List of execution results
        """
        results: List[ExecutionResult] = []
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])

        dependencies = self._build_dependency_graph(nodes, edges)
        execution_order = self._topological_sort(nodes, dependencies)

        # Reset retry counters for this DAG execution
        self._node_retry_counts.clear()

        for level_idx, level in enumerate(execution_order):
            tasks = []
            for node_id in level:
                node = self._find_node_by_id(nodes, node_id)
                if node:
                    tasks.append(
                        self._execute_node_with_retry(
                            node, context, results, retry_on_failure=retry_on_failure
                        )
                    )

            if tasks:
                level_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in level_results:
                    if isinstance(res, ExecutionResult):
                        results.append(res)
                    elif isinstance(res, Exception):
                        # Create a failure result for exceptions during execution
                        results.append(
                            ExecutionResult(
                                node_id="unknown",
                                success=False,
                                error=str(res),
                                execution_time=0.0,
                            )
                        )

        return results

    async def _execute_node_with_retry(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
        previous_results: List[ExecutionResult],
        retry_on_failure: bool = True,
    ) -> ExecutionResult:
        """
        Execute a node with exponential backoff retry.

        Args:
            node: Node to execute
            context: Execution context
            previous_results: Previous execution results
            retry_on_failure: Whether to retry on failure

        Returns:
            ExecutionResult
        """
        node_id = node.get("id", "unknown")
        node_name = node.get("name", node_id)
        tool_id = node.get("tool_id", node_name)

        last_error = None
        start_time = datetime.now()

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Check circuit breaker
                cb = self.get_circuit_breaker(tool_id)
                result = await cb.call_async(
                    self._execute_node, node, context, previous_results
                )

                # Record execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                result.execution_time = execution_time
                self._execution_times[node_id].append(execution_time)

                return result

            except CircuitBreakerOpenError as e:
                # Circuit is open, don't retry — send to dead letter queue
                self.dead_letter_queue.append(
                    {
                        "node_id": node_id,
                        "node": node,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "attempt": attempt,
                    }
                )
                execution_time = (datetime.now() - start_time).total_seconds()
                return ExecutionResult(
                    node_id=node_id,
                    success=False,
                    error=f"Circuit breaker open: {str(e)}",
                    execution_time=execution_time,
                )

            except Exception as e:
                last_error = e
                self._node_retry_counts[node_id] += 1

                if attempt < self.retry_config.max_retries and retry_on_failure:
                    # Check if this exception is retryable
                    if isinstance(e, self.retry_config.retryable_exceptions):
                        delay = self._calculate_backoff(attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Non-retryable error
                        break
                else:
                    # Max retries exhausted
                    break

        # All retries failed
        self.dead_letter_queue.append(
            {
                "node_id": node_id,
                "node": node,
                "error": str(last_error),
                "timestamp": datetime.now().isoformat(),
                "attempt": self._node_retry_counts[node_id],
            }
        )

        execution_time = (datetime.now() - start_time).total_seconds()
        return ExecutionResult(
            node_id=node_id,
            success=False,
            error=f"Failed after {self._node_retry_counts[node_id]} retries: {str(last_error)}",
            execution_time=execution_time,
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)

        if self.retry_config.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return delay

    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get all items in the dead letter queue."""
        return list(self.dead_letter_queue)

    def clear_dead_letter_queue(self):
        """Clear the dead letter queue."""
        self.dead_letter_queue.clear()

    def retry_dead_letter(self, context: Dict[str, Any]) -> List[ExecutionResult]:
        """
        Retry all items in the dead letter queue (synchronous wrapper).

        Args:
            context: Execution context

        Returns:
            List of execution results
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.retry_dead_letter_async(context)
        )

    async def retry_dead_letter_async(self, context: Dict[str, Any]) -> List[ExecutionResult]:
        """
        Retry all items in the dead letter queue asynchronously.

        Args:
            context: Execution context

        Returns:
            List of execution results
        """
        results = []
        items = list(self.dead_letter_queue)
        self.dead_letter_queue.clear()

        for item in items:
            result = await self._execute_node_with_retry(
                item["node"], context, [], retry_on_failure=True
            )
            results.append(result)

        return results

    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive execution statistics.

        Returns:
            Statistics dictionary
        """
        total_retries = sum(self._node_retry_counts.values())
        total_executions = sum(len(times) for times in self._execution_times.values())

        cb_stats = {
            name: {
                "state": cb.state.value,
                "failures": cb.total_failures,
                "successes": cb.total_successes,
            }
            for name, cb in self.circuit_breakers.items()
        }

        avg_times = {}
        for node_id, times in self._execution_times.items():
            if times:
                avg_times[node_id] = sum(times) / len(times)

        return {
            "total_retries": total_retries,
            "total_executions": total_executions,
            "dead_letter_count": len(self.dead_letter_queue),
            "circuit_breakers": cb_stats,
            "average_execution_times": avg_times,
            "retry_distribution": dict(self._node_retry_counts),
        }

    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers to CLOSED state."""
        for cb in self.circuit_breakers.values():
            cb.reset()

    def clear_all(self):
        """Clear all state: caches, dead letters, circuit breakers, stats."""
        self.clear_cache()
        self.clear_dead_letter_queue()
        self.circuit_breakers.clear()
        self._node_retry_counts.clear()
        self._execution_times.clear()
