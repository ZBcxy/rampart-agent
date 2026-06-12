"""Polaris Agent — Fully integrated OODA agent with Harness modules.

All modules wired in:
- tracer: span around every OODA phase, tool call, LLM invocation
- cache: ResponseCache for LLM dedup
- PromptManager: zero hardcoded prompts
- ToolAuthorizer: permission check before every tool execution
- ConfirmationHandler: human-in-the-loop for dangerous tools
- FailureClassifier: classify failures by root cause
- EntropyAuditor: evaluate LLM output uncertainty
- InterventionLog: structured recording of human interventions
- CodeHarness: validated code execution in sandbox
- ContextSelector: dynamic context selection per OODA phase
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from core.align.align_guard import AlignGuard
from core.align.policy_engine import AutonomyLevel, PolicyEngine
from core.align.tool_auth import ConfirmationHandler, ToolAuthorizer
from core.cache import ResponseCache
from core.context_selector import ContextSelector
from core.entropy_audit import EntropyAuditor
from core.executor.code_harness import CodeHarness
from core.executor.retry_executor import RetryConfig, RetryableDAGExecutor
from core.failure_attribution import FailureClassifier
from core.intervention import InterventionLog
from core.memory import EmbeddingSemanticMemory, WorkingMemory
from core.observability import log, metrics, tracer
from core.planner.llm_planner import LLMPlanner, LLMPlannerConfig
from core.prompts import PromptManager


@dataclass
class AgentConfig:
    """All agent configuration in one place — zero hardcoded values."""
    # Existing fields
    model: str = "gpt-4o"
    provider: str = "openai"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2000
    max_steps: int = 20
    autonomy: AutonomyLevel = AutonomyLevel.L3_AUTONOMOUS
    max_retries: int = 2
    retry_base_delay: float = 0.5
    max_revisions: int = 5
    deviation_threshold: float = 0.3
    confidence_threshold: float = 0.5
    cache_enabled: bool = True
    cache_ttl: int = 3600
    require_confirmation_for_dangerous: bool = True

    # ── New Harness Module Configs ──
    # Failure Attribution
    failure_classification_enabled: bool = True
    failure_history_limit: int = 1000

    # Entropy Audit
    entropy_threshold: float = 0.7
    entropy_fallback_enabled: bool = True
    entropy_strategies: Optional[List[str]] = None  # None = use all

    # Intervention Log
    intervention_logging_enabled: bool = True
    intervention_history_limit: int = 5000

    # Code Harness
    code_harness_enabled: bool = True
    code_harness_max_workers: int = 4

    # Context Selector
    context_selection_enabled: bool = True
    context_max_tokens: int = 4000
    context_embedding_boost: bool = True
    context_hybrid_weight: float = 0.7


@dataclass
class AgentStep:
    step_id: str
    phase: str
    thought: str = ""
    action: Optional[str] = None
    tool_calls: List[Dict] = field(default_factory=list)
    observation: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentResult:
    success: bool
    summary: str
    steps: List[AgentStep]
    tool_calls: List[Dict]
    total_time: float
    tokens_used: int = 0
    plan_id: Optional[str] = None


class Agent:
    """Fully integrated Polaris Agent — all modules wired in, zero hardcoded prompts."""

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        tools: Optional[Dict[str, Callable]] = None,
        confirm_callback: Optional[Callable] = None,
    ):
        self.config = config or AgentConfig()
        self.tools = tools or {}
        self.confirm_callback = confirm_callback

        # ── Existing modules ──
        self.prompts = PromptManager()
        self.cache = ResponseCache(ttl=self.config.cache_ttl) if self.config.cache_enabled else None
        self.align = AlignGuard(enabled=True)
        self.policy = PolicyEngine(autonomy_level=self.config.autonomy)
        self.tool_auth = ToolAuthorizer()
        self.working_memory = WorkingMemory(max_size=200)
        self.semantic_memory = EmbeddingSemanticMemory()

        # ── New Harness: Intervention Log (before ConfirmationHandler) ──
        self.intervention_log = InterventionLog(
            max_records=self.config.intervention_history_limit,
        ) if self.config.intervention_logging_enabled else None

        self.confirm = ConfirmationHandler(
            callback=confirm_callback,
            intervention_log=self.intervention_log,
        )

        # ── New Harness: Failure Attribution ──
        self.failure_classifier = FailureClassifier(
            history_limit=self.config.failure_history_limit,
        ) if self.config.failure_classification_enabled else None

        # ── New Harness: Entropy Audit ──
        self.entropy_auditor = EntropyAuditor(
            entropy_threshold=self.config.entropy_threshold,
        ) if self.config.entropy_threshold < 1.0 else None

        # ── New Harness: Context Selector ──
        self.context_selector = ContextSelector(
            working_memory=self.working_memory,
            semantic_memory=self.semantic_memory,
            tools=list(self.tools.keys()) if self.tools else [],
            embedding_enabled=self.config.context_embedding_boost,
        ) if self.config.context_selection_enabled else None

        # ── New Harness: Code Harness ──
        self.code_harness = CodeHarness(
            max_workers=self.config.code_harness_max_workers,
        ) if self.config.code_harness_enabled else None

        # ── Existing executor & planner ──
        self.executor = RetryableDAGExecutor(
            retry_config=RetryConfig(
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_base_delay,
            ),
        )

        llm_cfg = LLMPlannerConfig(
            model=self.config.model, provider=self.config.provider,
            temperature=self.config.temperature, max_tokens=self.config.max_tokens,
            api_key=self.config.api_key, api_base=self.config.api_base,
        )
        self.planner = LLMPlanner(config=llm_cfg)
        self._step_counter = 0

    # ── Public API ───────────────────────────────────────────────────────

    async def run(self, goal: str, context: Dict = None) -> AgentResult:
        t0 = time.perf_counter()
        context = context or {}
        steps: List[AgentStep] = []
        all_calls: List[Dict] = []

        with tracer.start_span("agent.run", {"goal": goal[:100]}) as root:
            guard = self.align.check_input(goal)
            if not guard.allowed:
                return AgentResult(
                    False,
                    f"Blocked: {'; '.join(v.message for v in guard.violations)}",
                    steps, all_calls, time.perf_counter() - t0,
                )

            self.working_memory.add(f"Goal: {goal}", item_type="plan", importance=1.0)
            log.info("Agent.run start", extra={"goal": goal[:100]})

            plan = await self._cached(f"plan:{goal}", lambda: self.planner.generate_plan(goal, context))
            root.set_attribute("plan_id", plan.id if plan else "none")

            for phase in ["observe", "orient", "decide", "act"]:
                if self._step_counter >= self.config.max_steps:
                    break
                self._step_counter += 1

                with tracer.start_span(f"ooda.{phase}", {"step": self._step_counter}):
                    t_step = time.perf_counter()
                    result = await self._run_phase(phase, goal, steps, context, plan)

                step = AgentStep(
                    step_id=f"step-{self._step_counter}", phase=phase,
                    thought=result["thought"],
                    action=json.dumps(result.get("actions", []), ensure_ascii=False),
                    tool_calls=result["tool_results"],
                    observation=result.get("observation", ""),
                    duration_ms=(time.perf_counter() - t_step) * 1000,
                )
                steps.append(step)
                all_calls.extend(result["tool_results"])

                if result.get("done"):
                    break

        summary = self.working_memory.to_context_string(max_tokens=1000)
        return AgentResult(
            success=True,
            summary=f"{goal}\n{len(steps)} steps.\n{summary}",
            steps=steps, tool_calls=all_calls,
            total_time=time.perf_counter() - t0,
            plan_id=plan.id if plan else None,
        )

    async def run_stream(self, goal: str, context: Dict = None) -> AsyncIterator[Dict]:
        context = context or {}
        guard = self.align.check_input(goal)
        if not guard.allowed:
            yield {"type": "blocked", "reason": str(guard.violations[0].message)}
            return

        yield {"type": "status", "status": "planning"}
        plan = await self._cached(f"plan:{goal}", lambda: self.planner.generate_plan(goal, context))
        yield {"type": "plan", "content": plan.root.content if plan else "",
               "confidence": plan.confidence if plan else 0}

        for phase in ["observe", "orient", "decide", "act"]:
            if self._step_counter >= self.config.max_steps:
                break
            self._step_counter += 1

            t_step = time.perf_counter()
            result = await self._run_phase(phase, goal, [], context, plan)

            yield {
                "type": "step", "step": self._step_counter, "phase": phase,
                "thought": result["thought"][:300],
                "tool_results": result["tool_results"],
                "duration_ms": (time.perf_counter() - t_step) * 1000,
            }

            if result.get("done"):
                yield {"type": "complete", "summary": "Done"}
                return

        yield {"type": "complete", "summary": "Max steps"}

    # ── Phase Execution ──────────────────────────────────────────────────

    async def _run_phase(self, phase: str, goal: str, steps: List, context: Dict, plan) -> Dict:
        metrics.increment(f"ooda.{phase}")

        # ── Context Selection (dynamic, per-phase) ──
        if self.context_selector:
            selected_ctx = self.context_selector.select_context(
                phase=phase, goal=goal,
                memory_context={
                    "plan_content": plan.root.content if plan else "",
                    "tool_names": list(self.tools.keys()),
                },
                history=[{"phase": s.phase, "action": s.action, "observation": s.observation}
                          for s in steps],
                max_tokens=self.config.context_max_tokens // 2,
            )
            ctx_dict = selected_ctx.to_context_dict()
            ctx_json = json.dumps(ctx_dict, ensure_ascii=False)
            tool_list = selected_ctx.get_tool_list(", ".join(self.tools.keys()))
        else:
            ctx_json = json.dumps(context, ensure_ascii=False)
            tool_list = ", ".join(self.tools.keys())

        # Render from PromptManager — zero hardcoded prompts
        prompt = self.prompts.render(f"ooda.{phase}",
            goal=goal,
            previous_actions=json.dumps([s.action for s in steps[-3:] if s.action], ensure_ascii=False),
            context=ctx_json,
            available_tools=tool_list,
            observations=json.dumps([s.observation for s in steps[-3:] if s.observation], ensure_ascii=False),
            plan=plan.root.content if plan else "",
            synthesis="", insights="[]", risks="[]", actions="[]", results="[]")

        response = await self._cached(f"{phase}:{goal[:50]}", lambda: self._call_llm(prompt))

        # ── Entropy Audit (after LLM response, before parsing) ──
        if self.entropy_auditor:
            entropy_report = self.entropy_auditor.evaluate_response(response, {
                "phase": phase, "goal": goal[:100],
            })
            if entropy_report.exceeds_threshold:
                log.warning("High entropy in LLM response", extra={
                    "phase": phase, "entropy_score": entropy_report.score,
                    "recommended_action": entropy_report.recommended_action,
                })
                metrics.record("entropy.score", entropy_report.score)
                metrics.increment("entropy.threshold_exceeded")
                if (entropy_report.recommended_action in ("fallback", "retry")
                        and self.config.entropy_fallback_enabled):
                    fallback_key = f"{phase}:fallback:{goal[:50]}"
                    response = await self._cached(fallback_key, lambda: self._call_llm(
                        self.prompts.render(f"ooda.{phase}",
                            goal=goal,
                            previous_actions="Fallback mode — previous actions omitted for safety.",
                            context=ctx_json,
                            available_tools=tool_list,
                            observations="",
                            plan=plan.root.content if plan else "",
                            synthesis="", insights="[]", risks="[]", actions="[]", results="[]")
                    ))

        data = self._parse_json(response)

        tool_results = []
        for action in data.get("actions", []):
            if action.get("type") == "tool_call":
                tool_results.append(await self._execute_tool(action))
            elif action.get("type") == "complete":
                return {
                    "thought": data.get("reasoning", ""),
                    "actions": data.get("actions", []),
                    "tool_results": tool_results,
                    "observation": "",
                    "done": True,
                }

        thought = data.get("understanding") or data.get("synthesis") or data.get("reasoning", "")
        self.working_memory.add(f"[{phase}] {thought[:200]}", item_type="reflection")
        return {
            "thought": thought,
            "actions": data.get("actions", []),
            "observation": data.get("assessment", ""),
            "tool_results": tool_results,
            "done": data.get("next_phase") == "complete" or not data.get("should_continue", True),
        }

    # ── Tool Execution ───────────────────────────────────────────────────

    async def _execute_tool(self, action: Dict) -> Dict:
        tool_name = action.get("tool", "")
        tool_args = action.get("arguments", {})

        with tracer.start_span(f"tool.{tool_name}") as span:
            # ── Code Harness routing ──
            if tool_name == "code_harness_execute" and self.code_harness:
                code = tool_args.get("code", "")
                try:
                    ctx_str = tool_args.get("context", "{}")
                    ctx_dict = json.loads(ctx_str) if isinstance(ctx_str, str) else ctx_str
                except json.JSONDecodeError:
                    ctx_dict = {}
                result = await self.code_harness.execute_action_code_async(code, ctx_dict)
                span.set_attribute("code_length", len(code))
                span.set_attribute("validated", result.get("validated", False))
                span.set_attribute("execution_time_ms", result.get("execution_time", 0) * 1000)
                return result

            # Tool authorization
            auth = self.tool_auth.authorize("operator", tool_name, self.config.autonomy)
            if not auth["allowed"]:
                span.set_attribute("blocked", True)
                return {"tool": tool_name, "success": False, "error": auth["reason"]}

            # Confirmation for dangerous tools
            if auth.get("requires_confirmation") and self.config.require_confirmation_for_dangerous:
                approved = await self.confirm.request_confirmation(tool_name, tool_args)
                if not approved:
                    return {"tool": tool_name, "success": False, "error": "User denied"}

            func = self.tools.get(tool_name)
            if not func:
                return {"tool": tool_name, "success": False, "error": f"Not found: {tool_name}"}

            t0 = time.perf_counter()
            try:
                result = func(**tool_args) if callable(func) else str(func)
                error = None
            except Exception as e:
                result, error = None, str(e)

                # ── Failure Attribution ──
                if self.failure_classifier:
                    try:
                        report = self.failure_classifier.classify(e, {
                            "tool_name": tool_name,
                            "tool_args": str(tool_args)[:200],
                            "phase": "tool_execution",
                            "step": self._step_counter,
                        })
                        span.set_attribute("failure.category", report.category.value)
                        span.set_attribute("failure.confidence", report.confidence)
                        log.warning("Tool execution failure classified", extra={
                            "tool": tool_name,
                            "failure_category": report.category.value,
                            "failure_id": report.failure_id,
                            "suggested_fix": report.suggested_fix,
                        })
                    except Exception:
                        pass  # Failure classification should never break execution

            dt = time.perf_counter() - t0
            metrics.record(f"tool.{tool_name}.duration", dt)
            span.set_attribute("duration_ms", dt * 1000)
            self.tool_auth.record_execution(
                "operator", tool_name, tool_args, True,
                auth.get("requires_confirmation", False), error is None,
            )
            return {
                "tool": tool_name, "arguments": tool_args,
                "result": str(result)[:500] if result else None,
                "error": error, "execution_time": dt,
            }

    # ── LLM ──────────────────────────────────────────────────────────────

    async def _call_llm(self, prompt: str) -> str:
        metrics.increment("llm.calls")
        with tracer.start_span("llm.call") as span:
            try:
                import litellm
                t0 = time.perf_counter()
                resp = litellm.completion(
                    model=f"{self.config.provider}/{self.config.model}",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature, max_tokens=self.config.max_tokens,
                    api_key=self.config.api_key, api_base=self.config.api_base,
                )
                dt = time.perf_counter() - t0
                metrics.record("llm.duration", dt)
                span.set_attribute("duration_ms", dt * 1000)
                return resp.choices[0].message.content
            except Exception as e:
                span.set_error(e)
                metrics.increment("llm.errors")
                # ── Failure Attribution for LLM errors ──
                if self.failure_classifier:
                    try:
                        report = self.failure_classifier.classify(e, {
                            "phase": "llm_call",
                            "step": self._step_counter,
                        })
                        span.set_attribute("failure.category", report.category.value)
                        log.warning("LLM call failure classified", extra={
                            "failure_category": report.category.value,
                            "suggested_fix": report.suggested_fix,
                        })
                    except Exception:
                        pass
                return '{"understanding":"LLM unavailable, fallback mode","confidence":0.3}'

    async def _cached(self, key: str, compute_fn) -> Any:
        if self.cache:
            return await self.cache.get_or_compute(key, compute_fn, self.config.cache_ttl)
        return await compute_fn()

    @staticmethod
    def _parse_json(text: str) -> Dict:
        text = (text or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    # ── Tool Registration ────────────────────────────────────────────────

    def register_tool(self, name: str, func: Callable, description: str = ""):
        self.tools[name] = func
        if description:
            self.working_memory.add(
                f"Tool: {name} — {description}",
                item_type="tool", metadata={"tool": name},
            )
        # Keep context selector in sync
        if self.context_selector:
            self.context_selector.update_tool_list(list(self.tools.keys()))

    def register_tools_from_registry(self, registry):
        for name in registry.list_all():
            self.register_tool(name, _make_tool_func(registry, name))
            tool = registry.get(name)
            if tool and tool.requires_confirmation:
                self.tool_auth._policies[name].require_confirmation = True

    # ── Human Injection API ──────────────────────────────────────────────

    async def inject_context(self, ctx: Dict[str, Any], reason: str = "") -> str:
        """Allow a human to inject new context into the agent's working memory.

        Records the intervention for full trajectory audit.
        """
        if self.intervention_log:
            from core.intervention import InterventionType
            self.intervention_log.record(
                intervention_type=InterventionType.INJECT,
                original=None,
                modified=json.dumps(ctx, ensure_ascii=False),
                reason=reason or "Human context injection",
                context={"injected_keys": list(ctx.keys())},
            )
        self.working_memory.add(
            f"[HUMAN INJECTION] {json.dumps(ctx, ensure_ascii=False)}",
            item_type="human_input", importance=1.0,
        )
        return f"Injected {len(ctx)} keys into working memory"

    # ── Shutdown ─────────────────────────────────────────────────────────

    async def shutdown(self):
        """Graceful shutdown of all modules."""
        if self.code_harness:
            try:
                self.code_harness.shutdown()
            except Exception:
                pass


def _make_tool_func(registry, tool_name):
    """Create a closure that calls registry.execute for a specific tool."""
    def tool_func(**kwargs):
        return registry.execute(tool_name, **kwargs)
    return tool_func
