"""Observability: Structured Logging + Span Tracing

Provides OpenTelemetry-compatible tracing across the entire agent lifecycle.
Each OODA phase, tool call, and LLM invocation creates a span with metadata.

Usage:
    from core.observability import tracer, log, SpanContext

    with tracer.start_span("ooda.observe") as span:
        span.set_attribute("goal", goal)
        log.info("Observing environment", extra={"phase": "observe"})
"""

import functools
import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# ── Structured JSON Logger ──────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include extra fields
        for key in ("span_id", "trace_id", "phase", "tool", "model", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Include exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", json_format: bool = True):
    """Configure structured logging for the agent."""
    logger = logging.getLogger("polaris")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
    logger.addHandler(handler)
    return logger


log = setup_logging()


# ── Span Tracing ─────────────────────────────────────────────────────────────

@dataclass
class Span:
    """A single execution span in the trace tree."""

    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_id: Optional[str] = None
    name: str = ""
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok | error
    children: List["Span"] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        self.events.append({
            "name": name,
            "timestamp": time.perf_counter(),
            "attributes": attributes or {},
        })

    def set_error(self, error: Exception):
        self.status = "error"
        self.set_attribute("error.type", type(error).__name__)
        self.set_attribute("error.message", str(error))

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.perf_counter()
        return (end - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "children": [c.to_dict() for c in self.children],
        }


class Tracer:
    """Lightweight span tracer compatible with OpenTelemetry concepts.

    Not a full OTLP exporter, but follows the same mental model.
    Can be extended to export to Jaeger/Zipkin/OTLP.
    """

    def __init__(self, name: str = "polaris-agent"):
        self.name = name
        self._spans: List[Span] = []
        self._active: List[Span] = []
        self._exporters: List[Callable] = []

    @contextmanager
    def start_span(self, name: str, attributes: Dict[str, Any] = None):
        """Context manager for a traced span."""
        parent = self._active[-1] if self._active else None
        span = Span(
            name=name,
            trace_id=parent.trace_id if parent else uuid.uuid4().hex[:16],
            parent_id=parent.span_id if parent else None,
        )
        if attributes:
            span.attributes.update(attributes)

        self._active.append(span)

        # Log span start
        log.debug(f"Span start: {name}", extra={
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "phase": name,
        })

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            span.end_time = time.perf_counter()
            self._active.pop()

            if parent:
                parent.children.append(span)
            else:
                self._spans.append(span)

            # Log span end
            log.debug(f"Span end: {name}", extra={
                "span_id": span.span_id,
                "duration_ms": round(span.duration_ms, 2),
                "status": span.status,
            })

            # Export
            for exporter in self._exporters:
                try:
                    exporter(span)
                except Exception:
                    pass

    def trace(self, name: str = None, attributes: Dict[str, Any] = None):
        """Decorator to trace a function call."""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__qualname__

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.start_span(span_name, attributes) as span:
                    span.set_attribute("function", func.__qualname__)
                    return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.start_span(span_name, attributes) as span:
                    span.set_attribute("function", func.__qualname__)
                    return func(*args, **kwargs)

            import inspect
            return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def add_exporter(self, exporter: Callable[[Span], None]):
        """Add a span exporter (e.g., console, OTLP, file)."""
        self._exporters.append(exporter)

    def get_trace_tree(self) -> List[Dict[str, Any]]:
        """Get the full trace tree as a list of root spans."""
        return [s.to_dict() for s in self._spans]

    def flush(self):
        """Export all pending spans."""
        for span in self._spans:
            for exporter in self._exporters:
                try:
                    exporter(span)
                except Exception:
                    pass

    def clear(self):
        """Clear all spans."""
        self._spans.clear()


# Global tracer instance
tracer = Tracer()


# ── Console Exporter ─────────────────────────────────────────────────────────

def console_exporter(span: Span):
    """Simple console exporter for development."""
    import json as _json
    print(f"[TRACE] {span.name}: {span.duration_ms:.1f}ms status={span.status}", file=sys.stderr)


tracer.add_exporter(console_exporter)


# ── Metrics ──────────────────────────────────────────────────────────────────

@dataclass
class MetricsCollector:
    """Simple in-process metrics collector."""

    counters: Dict[str, int] = field(default_factory=dict)
    histograms: Dict[str, List[float]] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1):
        self.counters[name] = self.counters.get(name, 0) + value

    def record(self, name: str, value: float):
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def gauge(self, name: str, value: float):
        self.gauges[name] = value

    def snapshot(self) -> Dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "histograms": {
                k: {
                    "count": len(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "p50": sorted(v)[len(v)//2] if v else 0,
                    "p95": sorted(v)[int(len(v)*0.95)] if len(v) >= 20 else (max(v) if v else 0),
                }
                for k, v in self.histograms.items()
            },
            "gauges": dict(self.gauges),
        }


metrics = MetricsCollector()


# ── Health Check ─────────────────────────────────────────────────────────────

def health_check() -> Dict[str, Any]:
    """Agent health status."""
    import platform

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.1.0",
        "python": sys.version,
        "platform": platform.platform(),
        "metrics": metrics.snapshot(),
        "active_spans": len(tracer._active),
        "total_spans": len(tracer._spans),
    }
