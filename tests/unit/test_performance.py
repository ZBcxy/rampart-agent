import pytest
import time
from core.performance import (
    PerformanceMonitor,
    performance_monitor,
    monitor_function,
    benchmark,
    async_benchmark,
    BenchmarkResult,
)


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor"""

    def setup_method(self):
        """Reset monitor before each test"""
        performance_monitor.reset_all()

    def test_record_measurement(self):
        """Test recording a performance measurement"""
        monitor = PerformanceMonitor()
        monitor.record("test_op", 0.1, success=True)

        metric = monitor.get_metric("test_op")
        assert metric is not None
        assert metric.call_count == 1
        assert metric.total_time == 0.1
        assert metric.success_count == 1

    def test_measure_decorator(self):
        """Test the measure decorator"""
        monitor = PerformanceMonitor()

        @monitor.measure("decorated_func", tags=["test"])
        def test_func():
            time.sleep(0.01)
            return "result"

        result = test_func()
        assert result == "result"

        metric = monitor.get_metric("decorated_func")
        assert metric is not None
        assert metric.call_count == 1
        assert metric.success_count == 1

    def test_measure_decorator_async(self):
        """Test the measure decorator with async functions"""
        import asyncio
        monitor = PerformanceMonitor()

        @monitor.measure("async_func", tags=["async"])
        async def test_func():
            await asyncio.sleep(0.01)
            return "async_result"

        result = asyncio.run(test_func())
        assert result == "async_result"

        metric = monitor.get_metric("async_func")
        assert metric is not None
        assert metric.call_count == 1

    def test_global_monitor_decorator(self):
        """Test the global monitor decorator"""

        @monitor_function()
        def global_test_func():
            return "global_result"

        result = global_test_func()
        assert result == "global_result"

    def test_error_tracking(self):
        """Test that errors are tracked correctly"""
        monitor = PerformanceMonitor()

        @monitor.measure("error_func")
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_func()

        metric = monitor.get_metric("error_func")
        assert metric is not None
        assert metric.error_count == 1

    def test_tags(self):
        """Test that tags work correctly"""
        monitor = PerformanceMonitor()
        monitor.record("op1", 0.1, tags=["tag1", "tag2"])
        monitor.record("op2", 0.2, tags=["tag2", "tag3"])

        metrics = monitor.get_metrics_by_tag("tag2")
        assert len(metrics) == 2

        metrics = monitor.get_metrics_by_tag("tag1")
        assert len(metrics) == 1

    def test_slowest_metrics(self):
        """Test getting slowest metrics"""
        monitor = PerformanceMonitor()
        monitor.record("fast_op", 0.01)
        monitor.record("medium_op", 0.1)
        monitor.record("slow_op", 1.0)

        slowest = monitor.get_slowest_metrics(2)
        assert len(slowest) == 2
        assert slowest[0].name == "slow_op"

    def test_most_frequent_metrics(self):
        """Test getting most frequent metrics"""
        monitor = PerformanceMonitor()
        for _ in range(10):
            monitor.record("frequent_op", 0.01)
        for _ in range(3):
            monitor.record("infrequent_op", 0.01)

        frequent = monitor.get_most_frequent_metrics(2)
        assert len(frequent) == 2
        assert frequent[0].name == "frequent_op"

    def test_statistics(self):
        """Test getting statistics"""
        monitor = PerformanceMonitor()
        monitor.record("op1", 0.1, success=True)
        monitor.record("op2", 0.2, success=True)
        monitor.record("op3", 0.3, success=False)

        stats = monitor.get_statistics()
        assert stats["total_operations"] == 3
        assert stats["overall_success_rate"] == 2 / 3

    def test_reset(self):
        """Test resetting metrics"""
        monitor = PerformanceMonitor()
        monitor.record("op1", 0.1)

        assert monitor.get_metric("op1") is not None

        monitor.reset("op1")
        assert monitor.get_metric("op1") is None

    def test_reset_all(self):
        """Test resetting all metrics"""
        monitor = PerformanceMonitor()
        monitor.record("op1", 0.1)
        monitor.record("op2", 0.2)

        assert len(monitor.metrics) == 2

        monitor.reset_all()
        assert len(monitor.metrics) == 0


class TestBenchmark:
    """Tests for benchmarking functions"""

    def test_sync_benchmark(self):
        """Test sync function benchmark"""

        def test_func():
            time.sleep(0.001)

        result = benchmark(test_func, iterations=10)
        assert isinstance(result, BenchmarkResult)
        assert result.iterations == 10
        assert result.total_time > 0
        assert result.mean_time > 0
        assert result.min_time <= result.mean_time <= result.max_time

    def test_async_benchmark(self):
        """Test async function benchmark"""
        import asyncio

        async def test_func():
            await asyncio.sleep(0.001)

        result = asyncio.run(
            async_benchmark(test_func, iterations=10)
        )
        assert isinstance(result, BenchmarkResult)
        assert result.iterations == 10

    def test_benchmark_statistics(self):
        """Test that benchmark produces correct statistics"""

        def consistent_func():
            time.sleep(0.01)

        result = benchmark(consistent_func, iterations=20)
        assert result.min_time > 0
        assert result.max_time >= result.min_time
        assert result.median_time > 0
        assert result.std_dev >= 0
        assert result.p95_time >= result.median_time
        assert result.p99_time >= result.p95_time
