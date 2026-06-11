"""Eval Framework — Assertion-based + LLM-as-Judge evaluation pipeline.

Usage:
    from core.eval import EvalSuite, AssertionEval, LLMJudgeEval

    suite = EvalSuite("planner_tests")
    suite.add(AssertionEval("plan_has_steps", lambda result: len(result.steps) > 0))
    suite.add(LLMJudgeEval("quality_check", "Is the plan logical and complete?"))
    report = await suite.run(agent, test_cases)
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional


@dataclass
class EvalCase:
    """A single evaluation test case."""
    id: str
    input: Dict[str, Any]
    expected: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of a single evaluation."""
    case_id: str
    eval_name: str
    passed: bool
    score: float = 0.0  # 0.0 - 1.0
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class EvalReport:
    """Aggregated evaluation report."""
    suite_name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: float = 0.0
    results: List[EvalResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def pass_rate(self) -> float:
        return self.passed / max(self.total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite": self.suite_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 3),
            "avg_score": round(self.avg_score, 3),
            "timestamp": self.timestamp,
            "results": [
                {
                    "case": r.case_id,
                    "eval": r.eval_name,
                    "passed": r.passed,
                    "score": r.score,
                    "reason": r.reason,
                }
                for r in self.results
            ],
        }


class AssertionEval:
    """Rule-based evaluation with assertion functions."""

    def __init__(self, name: str, check: Callable[[Any], bool], weight: float = 1.0):
        self.name = name
        self.check = check
        self.weight = weight

    async def evaluate(self, case: EvalCase, output: Any) -> EvalResult:
        t0 = time.perf_counter()
        try:
            passed = self.check(output)
            reason = "Assertion passed" if passed else "Assertion failed"
        except Exception as e:
            passed = False
            reason = f"Assertion error: {e}"

        return EvalResult(
            case_id=case.id,
            eval_name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            reason=reason,
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


class LLMJudgeEval:
    """LLM-as-Judge evaluation using a separate model call."""

    JUDGE_PROMPT = """You are an evaluator. Score the agent's output on the given criterion.

Criterion: ${criterion}

User Input: ${input}
Expected Output: ${expected}
Actual Output: ${output}

Score the output from 0.0 to 1.0 and explain your reasoning.
Output JSON: {"score": 0.0-1.0, "reasoning": "Your explanation"}"""

    def __init__(self, name: str, criterion: str, model: str = "gpt-4o", api_key: str = None):
        self.name = name
        self.criterion = criterion
        self.model = model
        self.api_key = api_key

    async def evaluate(self, case: EvalCase, output: Any) -> EvalResult:
        t0 = time.perf_counter()
        try:
            import litellm
            from string import Template

            prompt = Template(self.JUDGE_PROMPT).safe_substitute(
                criterion=self.criterion,
                input=json.dumps(case.input, ensure_ascii=False),
                expected=json.dumps(case.expected or {}, ensure_ascii=False),
                output=json.dumps(str(output), ensure_ascii=False),
            )

            resp = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
                api_key=self.api_key,
            )

            content = resp.choices[0].message.content
            result = json.loads(self._extract_json(content))
            score = float(result.get("score", 0.5))
            reason = result.get("reasoning", "No reasoning provided")

        except Exception as e:
            score = 0.0
            reason = f"Judge evaluation failed: {e}"

        return EvalResult(
            case_id=case.id,
            eval_name=self.name,
            passed=score >= 0.5,
            score=score,
            reason=reason,
            duration_ms=(time.perf_counter() - t0) * 1000,
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM response."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
            if text.endswith("```"):
                text = text[:-3]
        return text


class EvalSuite:
    """Runs multiple evaluations across test cases."""

    def __init__(self, name: str):
        self.name = name
        self.evals: List[Any] = []  # AssertionEval | LLMJudgeEval
        self.cases: List[EvalCase] = []

    def add(self, evaluator):
        self.evals.append(evaluator)

    def add_case(self, case_id: str, input_data: Dict, expected: Dict = None, **metadata):
        self.cases.append(EvalCase(id=case_id, input=input_data, expected=expected, metadata=metadata))

    def add_cases(self, cases: List[Dict]):
        for c in cases:
            self.add_case(c["id"], c.get("input", {}), c.get("expected"), **c.get("metadata", {}))

    async def run(self, runner: Callable[[EvalCase], Coroutine]) -> EvalReport:
        """Run all evals against all cases.

        Args:
            runner: Async function that takes an EvalCase and returns the agent's output
        """
        results = []

        for case in self.cases:
            try:
                output = await runner(case)
            except Exception as e:
                output = f"ERROR: {e}"

            for evaluator in self.evals:
                result = await evaluator.evaluate(case, output)
                results.append(result)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / max(total, 1)

        return EvalReport(
            suite_name=self.name,
            total=total,
            passed=passed,
            failed=total - passed,
            avg_score=avg_score,
            results=results,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "evaluators": [e.name for e in self.evals],
            "cases": [{"id": c.id, "input_keys": list(c.input.keys())} for c in self.cases],
        }


# ── Pre-built evaluators ─────────────────────────────────────────────────────

def eval_plan_has_steps(result) -> bool:
    """Check that a plan has execution steps."""
    return hasattr(result, "steps") and len(result.steps) > 0


def eval_no_error(result) -> bool:
    """Check that execution completed without errors."""
    return hasattr(result, "success") and result.success


def eval_response_length(min_chars: int = 50):
    """Check that the response meets minimum length."""
    return lambda result: len(str(result)) >= min_chars


def eval_confidence_above(threshold: float = 0.5):
    """Check that plan confidence exceeds threshold."""
    return lambda plan: hasattr(plan, "confidence") and plan.confidence >= threshold


def eval_tool_called(tool_name: str):
    """Check that a specific tool was called."""
    return lambda result: any(
        tc.name == tool_name
        for tc in (result.tool_calls if hasattr(result, "tool_calls") else [])
    )
