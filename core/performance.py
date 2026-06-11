import asyncio
import functools
import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class PerformanceMetric:
    """Performance metric entry"""

    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_called: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def average_time(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_time / self.call_count

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time": self.total_time,
            "average_time": self.average_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0,
            "max_time": self.max_time,
            "last_called": self.last_called.isoformat() if self.last_called else None,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "metadata": self.metadata,
        }


class PerformanceMonitor:
    """Performance monitoring and profiling system"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.tags: Dict[str, List[str]] = defaultdict(list)
        self._start_time: Optional[float] = None

    def measure(self, name: str, tags: Optional[List[str]] = None) -> Callable:
        """Decorator to measure function performance"""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return await func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    self.record(
                        name, time.perf_counter() - start, success=True, tags=tags
                    )
                    return result
                except Exception as e:
                    self.record(
                        name, time.perf_counter() - start, success=False, tags=tags
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    self.record(
                        name, time.perf_counter() - start, success=True, tags=tags
                    )
                    return result
                except Exception as e:
                    self.record(
                        name, time.perf_counter() - start, success=False, tags=tags
                    )
                    raise

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def record(
        self,
        name: str,
        duration: float,
        success: bool = True,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a performance measurement"""
        if not self.enabled:
            return

        if name not in self.metrics:
            self.metrics[name] = PerformanceMetric(name=name)

        metric = self.metrics[name]
        metric.call_count += 1
        metric.total_time += duration
        metric.min_time = min(metric.min_time, duration)
        metric.max_time = max(metric.max_time, duration)
        metric.last_called = datetime.now()

        if success:
            metric.success_count += 1
        else:
            metric.error_count += 1

        if metadata:
            metric.metadata.update(metadata)

        if tags:
            for tag in tags:
                if name not in self.tags[tag]:
                    self.tags[tag].append(name)

    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get a specific metric"""
        return self.metrics.get(name)

    def get_metrics_by_tag(self, tag: str) -> List[PerformanceMetric]:
        """Get metrics by tag"""
        return [self.metrics[name] for name in self.tags.get(tag, []) if name in self.metrics]

    def get_slowest_metrics(self, limit: int = 10) -> List[PerformanceMetric]:
        """Get the slowest metrics by average time"""
        metrics = list(self.metrics.values())
        metrics.sort(key=lambda m: m.average_time, reverse=True)
        return metrics[:limit]

    def get_most_frequent_metrics(self, limit: int = 10) -> List[PerformanceMetric]:
        """Get the most frequently called metrics"""
        metrics = list(self.metrics.values())
        metrics.sort(key=lambda m: m.call_count, reverse=True)
        return metrics[:limit]

    def reset(self, name: Optional[str] = None):
        """Reset metrics"""
        if name:
            if name in self.metrics:
                del self.metrics[name]
        else:
            self.metrics.clear()

    def reset_all(self):
        """Reset all metrics and state"""
        self.metrics.clear()
        self.tags.clear()
        self._start_time = None

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        if not self.metrics:
            return {
                "total_operations": 0,
                "total_time": 0,
                "metrics": {},
            }

        total_operations = sum(m.call_count for m in self.metrics.values())
        total_time = sum(m.total_time for m in self.metrics.values())
        avg_time = total_time / total_operations if total_operations > 0 else 0
        overall_success_rate = (
            sum(m.success_count for m in self.metrics.values()) / total_operations
            if total_operations > 0
            else 1.0
        )

        return {
            "total_operations": total_operations,
            "total_time": total_time,
            "average_time_per_operation": avg_time,
            "overall_success_rate": overall_success_rate,
            "unique_metrics": len(self.metrics),
            "metrics": {name: m.to_dict() for name, m in self.metrics.items()},
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_function(name: Optional[str] = None, tags: Optional[List[str]] = None):
    """Decorator to monitor function performance (uses global monitor)"""

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__qualname__
        return performance_monitor.measure(func_name, tags)(func)

    return decorator


@dataclass
class BenchmarkResult:
    """Result from a benchmark run"""

    name: str
    iterations: int
    total_time: float
    mean_time: float
    median_time: float
    min_time: float
    max_time: float
    std_dev: float
    p95_time: float
    p99_time: float


def benchmark(func: Callable, iterations: int = 100, *args, **kwargs) -> BenchmarkResult:
    """
    Benchmark a function

    Args:
        func: Function to benchmark
        iterations: Number of iterations
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        BenchmarkResult with statistics
    """
    times = []

    # Warm-up
    for _ in range(5):
        func(*args, **kwargs)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    # Calculate statistics
    times.sort()
    total_time = sum(times)
    mean_time = total_time / iterations
    median_time = times[len(times) // 2]
    min_time = times[0]
    max_time = times[-1]

    # Standard deviation
    mean_diff_squared = sum((t - mean_time) ** 2 for t in times)
    std_dev = (mean_diff_squared / iterations) ** 0.5

    # Percentiles
    p95_time = times[int(iterations * 0.95)]
    p99_time = times[int(iterations * 0.99)]

    return BenchmarkResult(
        name=func.__name__,
        iterations=iterations,
        total_time=total_time,
        mean_time=mean_time,
        median_time=median_time,
        min_time=min_time,
        max_time=max_time,
        std_dev=std_dev,
        p95_time=p95_time,
        p99_time=p99_time,
    )


async def async_benchmark(func: Callable, iterations: int = 100, *args, **kwargs) -> BenchmarkResult:
    """Benchmark an async function"""
    times = []

    # Warm-up
    for _ in range(5):
        await func(*args, **kwargs)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    # Calculate statistics
    times.sort()
    total_time = sum(times)
    mean_time = total_time / iterations
    median_time = times[len(times) // 2]
    min_time = times[0]
    max_time = times[-1]
    mean_diff_squared = sum((t - mean_time) ** 2 for t in times)
    std_dev = (mean_diff_squared / iterations) ** 0.5
    p95_time = times[int(iterations * 0.95)]
    p99_time = times[int(iterations * 0.99)]

    return BenchmarkResult(
        name=func.__name__,
        iterations=iterations,
        total_time=total_time,
        mean_time=mean_time,
        median_time=median_time,
        min_time=min_time,
        max_time=max_time,
        std_dev=std_dev,
        p95_time=p95_time,
        p99_time=p99_time,
    )
