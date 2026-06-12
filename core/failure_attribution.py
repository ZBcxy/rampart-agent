"""Failure Attribution — classify Agent failures into root-cause categories.

Maps to the Harness paper's "故障归因" responsibility: distinguish whether
a failure is caused by:
- LLM reasoning errors (hallucination, bad planning, invalid JSON)
- Tool execution errors (timeout, permission, connection refused)
- Harness defects (circuit breaker, memory corruption, config errors)
- External factors (API unavailable, network unreachable)
"""

import re
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Tuple

from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    """Root-cause categories for agent failures."""
    LLM_REASONING = "llm_reasoning"
    TOOL_EXECUTION = "tool_execution"
    HARNESS_DEFECT = "harness_defect"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class FailureEvidence(BaseModel):
    """A piece of evidence contributing to the classification."""
    source: str  # "exception_type" | "error_message" | "stack_trace" | "pattern_match"
    detail: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class FailureReport(BaseModel):
    """Structured failure classification report."""
    failure_id: str = Field(default_factory=lambda: f"fail-{uuid.uuid4().hex[:8]}")
    category: FailureCategory = FailureCategory.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: List[FailureEvidence] = Field(default_factory=list)
    error_type: str = ""
    error_message: str = ""
    suggested_fix: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class FailureClassifier:
    """Classifies agent failures into root-cause categories.

    Uses multi-signal analysis: exception type hierarchy, error message
    regex patterns, and stack trace frame analysis to determine the
    most likely failure origin.
    """

    # ── Pattern Groups ───────────────────────────────────────────────────

    LLM_PATTERNS: List[Pattern] = [
        re.compile(r"(?i)hallucinat|confabulat|invent(?:ed|ion)\b"),
        re.compile(r"(?i)invalid\s+tool|unknown\s+tool|tool\s+.*\bnot\s+found"),
        re.compile(r"(?i)JSON\s*(?:parse|decod|invalid|error|malformed)|Expected\s+.*JSON"),
        re.compile(r"(?i)confidence\s+below\s+threshold"),
        re.compile(r"(?i)plan\s*(?:invalid|incomplete|malformed|empty)"),
        re.compile(r"(?i)unexpected\s+(?:token|format|response)"),
        re.compile(r"(?i)model\s+(?:generated|output|response)\s+(?:invalid|bad|wrong)"),
    ]

    TOOL_PATTERNS: List[Pattern] = [
        re.compile(r"(?i)time\s*out|timed?\s*out|timeout"),
        re.compile(r"(?i)permission|unauthorized|access\s+denied|forbidden"),
        re.compile(r"(?i)not\s+found|file\s+.*\bexist|no\s+such\s+(?:file|directory)"),
        re.compile(r"(?i)connection\s*(?:refused|reset|timeout|error)"),
        re.compile(r"(?i)sandbox|security\s+violation"),
        re.compile(r"(?i)rate\s+limit|too\s+many\s+requests"),
        re.compile(r"(?i)command\s+not\s+found|execution\s+failed"),
    ]

    HARNESS_PATTERNS: List[Pattern] = [
        re.compile(r"(?i)memory\s*(?:overflow|exhausted|limit|full)"),
        re.compile(r"(?i)circuit\s*(?:open|breaker)"),
        re.compile(r"(?i)dead\s*letter|max\s*retry|retry\s+exhausted"),
        re.compile(r"(?i)config\s*(?:invalid|missing|misconfig|error)"),
        re.compile(r"(?i)state\s*corrupt|inconsistent\s+state"),
        re.compile(r"(?i)policy\s*(?:violation|engine|blocked)"),
        re.compile(r"(?i)guard\s*(?:rejected|blocked|filtered)"),
    ]

    EXTERNAL_PATTERNS: List[Pattern] = [
        re.compile(r"(?i)API\s*(?:down|unavailable|error\s*[45]\d{2}|key\s+invalid)"),
        re.compile(r"(?i)provider\s*(?:error|unavailable|quota|overloaded)"),
        re.compile(r"(?i)network\s*(?:error|unreachable|h.?s.?t\s+unreachable)"),
        re.compile(r"(?i)HTTP\s*[45]\d{2}"),
        re.compile(r"(?i)DNS\s*(?:resolution|lookup|failure)"),
    ]

    # Exception class → category mapping
    EXCEPTION_TYPE_MAP: Dict[str, FailureCategory] = {
        "ToolExecutionError": FailureCategory.TOOL_EXECUTION,
        "SandboxError": FailureCategory.TOOL_EXECUTION,
        "SecurityViolationError": FailureCategory.TOOL_EXECUTION,
        "PlanGenerationError": FailureCategory.LLM_REASONING,
        "PlanValidationError": FailureCategory.LLM_REASONING,
        "ConfidenceError": FailureCategory.LLM_REASONING,
        "ContentFilterError": FailureCategory.HARNESS_DEFECT,
        "SafetyViolationError": FailureCategory.HARNESS_DEFECT,
        "CircuitBreakerOpenError": FailureCategory.HARNESS_DEFECT,
        "MemoryNotFoundError": FailureCategory.HARNESS_DEFECT,
        "MemoryStorageError": FailureCategory.HARNESS_DEFECT,
        "ConfigurationMissingError": FailureCategory.HARNESS_DEFECT,
        "ResourceExhaustedError": FailureCategory.HARNESS_DEFECT,
        "AuthenticationError": FailureCategory.EXTERNAL,
        "AuthorizationError": FailureCategory.EXTERNAL,
        "RateLimitError": FailureCategory.EXTERNAL,
        "TimeoutException": FailureCategory.TOOL_EXECUTION,
    }

    def __init__(self, history_limit: int = 1000):
        self._history: List[FailureReport] = []
        self._history_limit = history_limit

    # ── Public API ───────────────────────────────────────────────────────

    def classify(self, error: Exception, context: Optional[Dict] = None) -> FailureReport:
        """Classify a failure into a root-cause category.

        Args:
            error: The exception that occurred.
            context: Optional dict with keys like tool_name, phase, step, goal.

        Returns:
            FailureReport with category, confidence, evidence, and suggested fix.
        """
        context = context or {}
        evidence: List[FailureEvidence] = []
        err_msg = str(error)

        # 1. Classify by exception type hierarchy (strongest signal)
        cat_by_type = self._classify_by_exception_type(error)
        if cat_by_type and cat_by_type != FailureCategory.UNKNOWN:
            evidence.append(FailureEvidence(
                source="exception_type",
                detail=f"Exception class {type(error).__name__} maps to {cat_by_type.value}",
                weight=0.9,
            ))

        # 2. Classify by error message patterns
        msg_cat, msg_evidence = self._classify_by_message(err_msg)
        evidence.extend(msg_evidence)

        # 3. Classify by stack trace analysis
        trace_evidence = self._classify_by_stack_trace(error)
        evidence.extend(trace_evidence)

        # Aggregate scores per category
        scores: Dict[FailureCategory, float] = {}
        for ev in evidence:
            cat = self._evidence_weight_to_category(ev)
            if cat:
                scores[cat] = scores.get(cat, 0.0) + ev.weight

        # Pick highest-scoring category
        if msg_cat and msg_cat != FailureCategory.UNKNOWN:
            scores[msg_cat] = scores.get(msg_cat, 0.0) + 0.3  # Boost message match

        if cat_by_type and cat_by_type != FailureCategory.UNKNOWN:
            scores[cat_by_type] = scores.get(cat_by_type, 0.0) + 0.5  # Strong boost for type match

        if not scores:
            category = FailureCategory.UNKNOWN
            confidence = 0.1
        else:
            category = max(scores, key=lambda k: scores[k])
            max_score = scores[category]
            total_score = sum(scores.values()) + 0.1  # Smoothing
            confidence = min(max_score / total_score, 1.0)

        report = FailureReport(
            category=category,
            confidence=round(confidence, 2),
            evidence=evidence,
            error_type=type(error).__name__,
            error_message=err_msg[:500],
            suggested_fix=self._suggest_fix(category, context),
            context=context,
        )

        self._history.append(report)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]

        return report

    # ── Classification Methods ───────────────────────────────────────────

    def _classify_by_exception_type(self, error: Exception) -> Optional[FailureCategory]:
        """Classify based on the exception's class hierarchy."""
        err_type = type(error).__name__
        if err_type in self.EXCEPTION_TYPE_MAP:
            return self.EXCEPTION_TYPE_MAP[err_type]

        return FailureCategory.UNKNOWN

    def _classify_by_message(self, err_msg: str) -> Tuple[FailureCategory, List[FailureEvidence]]:
        """Classify based on error message regex patterns."""
        evidence: List[FailureEvidence] = []
        category_votes: Dict[FailureCategory, float] = {
            FailureCategory.LLM_REASONING: 0.0,
            FailureCategory.TOOL_EXECUTION: 0.0,
            FailureCategory.HARNESS_DEFECT: 0.0,
            FailureCategory.EXTERNAL: 0.0,
        }

        for pattern in self.LLM_PATTERNS:
            if pattern.search(err_msg):
                category_votes[FailureCategory.LLM_REASONING] += 0.15
                evidence.append(FailureEvidence(
                    source="pattern_match",
                    detail=f"Matched LLM pattern: {pattern.pattern}",
                    weight=0.15,
                ))

        for pattern in self.TOOL_PATTERNS:
            if pattern.search(err_msg):
                category_votes[FailureCategory.TOOL_EXECUTION] += 0.15
                evidence.append(FailureEvidence(
                    source="pattern_match",
                    detail=f"Matched tool pattern: {pattern.pattern}",
                    weight=0.15,
                ))

        for pattern in self.HARNESS_PATTERNS:
            if pattern.search(err_msg):
                category_votes[FailureCategory.HARNESS_DEFECT] += 0.15
                evidence.append(FailureEvidence(
                    source="pattern_match",
                    detail=f"Matched harness pattern: {pattern.pattern}",
                    weight=0.15,
                ))

        for pattern in self.EXTERNAL_PATTERNS:
            if pattern.search(err_msg):
                category_votes[FailureCategory.EXTERNAL] += 0.15
                evidence.append(FailureEvidence(
                    source="pattern_match",
                    detail=f"Matched external pattern: {pattern.pattern}",
                    weight=0.15,
                ))

        if all(v == 0.0 for v in category_votes.values()):
            return FailureCategory.UNKNOWN, evidence

        best_cat = max(category_votes, key=lambda k: category_votes[k])
        return best_cat, evidence

    def _classify_by_stack_trace(self, error: Exception) -> List[FailureEvidence]:
        """Analyze stack trace frames for origin hints."""
        evidence: List[FailureEvidence] = []
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        if "core/executor/" in tb_str or "sandbox" in tb_str.lower():
            evidence.append(FailureEvidence(
                source="stack_trace",
                detail="Error originated in executor/sandbox layer",
                weight=0.3,
            ))
        elif "core/planner/" in tb_str or "llm_planner" in tb_str:
            evidence.append(FailureEvidence(
                source="stack_trace",
                detail="Error originated in planner layer",
                weight=0.3,
            ))
        elif "core/align/" in tb_str or "core/agent" in tb_str:
            evidence.append(FailureEvidence(
                source="stack_trace",
                detail="Error originated in harness/alignment layer",
                weight=0.3,
            ))
        elif "litellm" in tb_str or "openai" in tb_str or "api" in tb_str.lower():
            evidence.append(FailureEvidence(
                source="stack_trace",
                detail="Error originated in external API call",
                weight=0.3,
            ))

        return evidence

    def _evidence_weight_to_category(self, ev: FailureEvidence) -> Optional[FailureCategory]:
        """Map an evidence item's detail to a category based on keywords."""
        detail = ev.detail.lower()
        if any(kw in detail for kw in ("llm", "planner", "json", "hallucin", "model generated")):
            return FailureCategory.LLM_REASONING
        if any(kw in detail for kw in ("tool", "sandbox", "security violation", "permission")):
            return FailureCategory.TOOL_EXECUTION
        if any(kw in detail for kw in ("harness", "circuit", "memory", "config", "guard", "policy")):
            return FailureCategory.HARNESS_DEFECT
        if any(kw in detail for kw in ("external", "api", "provider", "network", "dns", "http")):
            return FailureCategory.EXTERNAL
        return None

    # ── Suggested Fixes ──────────────────────────────────────────────────

    def _suggest_fix(self, category: FailureCategory, context: Dict) -> str:
        """Generate a human-readable suggested fix."""
        suggestions = {
            FailureCategory.LLM_REASONING: (
                "LLM reasoning error — consider: (1) simplifying the prompt, "
                "(2) providing explicit output format examples, (3) reducing task complexity, "
                "or (4) using a more capable model."
            ),
            FailureCategory.TOOL_EXECUTION: (
                "Tool execution error — consider: (1) checking tool input parameters, "
                "(2) verifying the tool/service is available, (3) increasing timeout, "
                "or (4) adding parameter validation in the tool implementation."
            ),
            FailureCategory.HARNESS_DEFECT: (
                "Harness defect — consider: (1) checking configuration values, "
                "(2) verifying resource limits (memory, token, step count), "
                "(3) resetting circuit breakers, or (4) reviewing policy engine rules."
            ),
            FailureCategory.EXTERNAL: (
                "External dependency error — consider: (1) verifying API keys and endpoints, "
                "(2) checking network connectivity, (3) implementing retry with exponential backoff, "
                "or (4) adding a fallback provider."
            ),
            FailureCategory.UNKNOWN: (
                "Unclassified failure — review full error trace and context, "
                "consider adding new classification patterns."
            ),
        }
        base = suggestions.get(category, suggestions[FailureCategory.UNKNOWN])
        tool = context.get("tool_name", "")
        if tool:
            base = f"[tool={tool}] {base}"
        return base

    # ── Statistics ───────────────────────────────────────────────────────

    def get_failure_statistics(self) -> Dict[str, Any]:
        """Aggregated failure classification statistics."""
        total = len(self._history)
        if total == 0:
            return {"total_failures": 0, "categories": {}, "avg_confidence": 0.0}

        cat_counts: Dict[str, int] = {}
        for report in self._history:
            cat = report.category.value
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        return {
            "total_failures": total,
            "categories": {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in cat_counts.items()},
            "avg_confidence": round(sum(r.confidence for r in self._history) / total, 2),
        }

    def get_recent_failures(self, limit: int = 20) -> List[FailureReport]:
        """Return recent failure reports."""
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear failure history."""
        self._history.clear()
