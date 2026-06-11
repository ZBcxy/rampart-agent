"""LLM-Powered Planner Module

Provides plan generation using real LLM calls via litellm.
Supports OpenAI, Anthropic, and other providers through a unified interface.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from .confidence import ConfidenceEvaluator
from .models import PlanNode, PlanTree


class LLMPlannerConfig:
    """Configuration for the LLM-powered planner."""

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str = "openai",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.api_base = api_base


# System prompt for plan generation
PLAN_GENERATION_PROMPT = """You are a planning agent that generates structured execution plans from user goals.
Given a user's goal and context, generate a detailed execution plan as a tree of actions.

The plan should be formatted as a JSON object with this structure:
{
    "goal_interpretation": "Brief restatement of the goal in clear terms",
    "reasoning": "Brief reasoning about the approach",
    "plan_tree": {
        "type": "action",  // One of: action, branch, parallel, human
        "content": "Description of this step",
        "confidence": 0.85,  // Your confidence in this step (0-1)
        "children": [
            // Nested plan nodes following the same structure
        ]
    }
}

Node types:
- "action": A concrete step to execute
- "branch": A decision point with alternative paths
- "parallel": Steps that can execute concurrently
- "human": A step requiring human input or confirmation

IMPORTANT RULES:
1. Generate ONLY valid JSON — no markdown, no extra text
2. Limit plan depth to 4 levels maximum
3. Each plan should have 3-8 steps at the top level
4. Confidence should reflect task complexity and clarity
5. Include specific, actionable content in each step
6. Use "parallel" nodes when steps are independent
7. Use "branch" nodes only when there are genuine alternatives

Context information:
{context}

User goal: {goal}

Generate the execution plan as JSON:"""

PLAN_REVISION_PROMPT = """You are revising an execution plan based on new observations.
The original plan encountered issues that require adjustment.

Original plan: {original_plan}

Failed observations: {observations}

Current context: {context}

Generate a revised plan as JSON with the same structure as the original.
Focus on:
1. Fixing or replacing failed steps
2. Adding fallback/retry steps where needed
3. Preserving successful parts of the plan
4. Reducing complexity where issues occurred

Generate the revised plan as JSON:"""


class LLMPlanner:
    """Planner that uses LLM calls for intelligent plan generation.

    Falls back to the rule-based Planner if no LLM provider is configured.
    """

    def __init__(self, config: Optional[LLMPlannerConfig] = None):
        """
        Initialize the LLM-powered planner.

        Args:
            config: LLM configuration. If None, uses rule-based fallback.
        """
        self.config = config
        self.confidence_evaluator = ConfidenceEvaluator()
        self._llm_available = False

        if config and config.api_key:
            self._llm_available = self._check_llm_availability()

    def _check_llm_availability(self) -> bool:
        """Check if litellm is available."""
        try:
            import litellm  # noqa: F401

            return True
        except ImportError:
            return False

    def generate_plan(self, goal: str, context: Dict[str, Any]) -> PlanTree:
        """
        Generate an execution plan from a goal.

        Uses LLM when available, falls back to rule-based planning.

        Args:
            goal: User goal description
            context: Context information (history, tools, etc.)

        Returns:
            PlanTree with generated plan
        """
        if not goal or not isinstance(goal, str):
            raise ValueError("目标必须是有效的字符串")

        if context is None:
            context = {}

        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        if self._llm_available and self.config:
            try:
                root_node = self._generate_with_llm(goal, context)
            except Exception:
                root_node = self._generate_with_rules(goal, context)
        else:
            root_node = self._generate_with_rules(goal, context)

        return PlanTree(
            id=plan_id,
            root=root_node,
            confidence=self.confidence_evaluator.evaluate_plan(
                PlanTree(id=plan_id, root=root_node)
            ),
        )

    def _generate_with_llm(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        Generate a plan using an LLM call via litellm.

        Args:
            goal: User goal
            context: Context information

        Returns:
            PlanNode root of the generated plan tree
        """
        import litellm

        context_str = json.dumps(
            {
                "history": [
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in context.get("history", [])
                ],
                "available_tools": context.get("available_tools", []),
                "environment": context.get("environment", {}),
            },
            ensure_ascii=False,
            indent=2,
        )

        prompt = PLAN_GENERATION_PROMPT.format(context=context_str, goal=goal)

        response = litellm.completion(
            model=f"{self.config.provider}/{self.config.model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        content = response.choices[0].message.content
        plan_data = self._parse_llm_response(content)

        return self._build_node_from_llm_output(plan_data.get("plan_tree", plan_data))

    def _generate_with_rules(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        Rule-based fallback plan generation.

        Args:
            goal: User goal
            context: Context information

        Returns:
            PlanNode root
        """
        goal_lower = goal.lower()

        if any(kw in goal_lower for kw in ["分析", "analysis", "analyze", "报告", "report"]):
            return self._build_analysis_plan(goal)
        elif any(kw in goal_lower for kw in ["创建", "create", "生成", "generate", "build", "make"]):
            return self._build_creation_plan(goal)
        elif any(kw in goal_lower for kw in ["搜索", "search", "查找", "find", "查询", "query"]):
            return self._build_search_plan(goal)
        elif any(kw in goal_lower for kw in ["部署", "deploy", "发布", "release", "安装", "install"]):
            return self._build_deploy_plan(goal)
        else:
            return self._build_default_plan(goal)

    def _build_analysis_plan(self, goal: str) -> PlanNode:
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"分析任务: {goal}",
            priority=1,
            confidence=0.85,
        )
        root.children = [
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="收集相关数据", priority=2, confidence=0.9),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="清洗和预处理数据", priority=3, confidence=0.85),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="执行数据分析", priority=4, confidence=0.8),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="生成分析报告", priority=5, confidence=0.85),
        ]
        return root

    def _build_creation_plan(self, goal: str) -> PlanNode:
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"创建任务: {goal}",
            priority=1,
            confidence=0.8,
        )
        root.children = [
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="分析需求和约束条件", priority=2, confidence=0.9),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="设计方案和架构", priority=3, confidence=0.85),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="实现核心功能", priority=4, confidence=0.75),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="验证和测试结果", priority=5, confidence=0.9),
        ]
        return root

    def _build_search_plan(self, goal: str) -> PlanNode:
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"搜索任务: {goal}",
            priority=1,
            confidence=0.9,
        )
        root.children = [
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="解析搜索查询", priority=2, confidence=0.95),
            PlanNode(
                id=f"node-{uuid.uuid4().hex[:8]}",
                type="parallel",
                content="并行搜索多个数据源",
                priority=3,
                confidence=0.85,
                children=[
                    PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="搜索本地知识库", priority=1, confidence=0.85),
                    PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="搜索网络资源", priority=1, confidence=0.8),
                ],
            ),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="聚合和排序搜索结果", priority=4, confidence=0.85),
        ]
        return root

    def _build_deploy_plan(self, goal: str) -> PlanNode:
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"部署任务: {goal}",
            priority=1,
            confidence=0.8,
        )
        root.children = [
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="验证部署前提条件", priority=2, confidence=0.9),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="准备部署包", priority=3, confidence=0.85),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="执行部署", priority=4, confidence=0.75),
            PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="验证部署结果", priority=5, confidence=0.9),
            PlanNode(
                id=f"node-{uuid.uuid4().hex[:8]}",
                type="branch",
                content="部署失败回滚",
                priority=6,
                confidence=0.7,
                children=[
                    PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="执行回滚操作", priority=1, confidence=0.85),
                    PlanNode(id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="发送失败通知", priority=2, confidence=0.9),
                ],
            ),
        ]
        return root

    def _build_default_plan(self, goal: str) -> PlanNode:
        return PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"执行任务: {goal}",
            priority=1,
            confidence=0.7,
        )

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        Parse the LLM response (may contain markdown code blocks).

        Args:
            content: Raw LLM response text

        Returns:
            Parsed plan data dict
        """
        content = content.strip()

        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re

            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError("Failed to parse LLM plan output as JSON")

    def _build_node_from_llm_output(self, data: Dict[str, Any]) -> PlanNode:
        """
        Recursively build a PlanNode tree from LLM JSON output.

        Args:
            data: Node data dict

        Returns:
            PlanNode
        """
        node_type = data.get("type", "action")
        if node_type not in ("action", "branch", "parallel", "human"):
            node_type = "action"

        children = []
        for child_data in data.get("children", []):
            children.append(self._build_node_from_llm_output(child_data))

        node = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type=node_type,
            content=data.get("content", ""),
            children=children,
            confidence=float(data.get("confidence", 0.7)),
            priority=data.get("priority", 1),
        )

        return node

    def revise_plan(self, current_plan: PlanTree, observations: List[Any]) -> PlanTree:
        """
        Revise a plan based on execution observations.

        Args:
            current_plan: The current plan that needs revision
            observations: List of execution observations

        Returns:
            Revised PlanTree
        """
        new_plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        if self._llm_available and self.config:
            try:
                return self._revise_with_llm(current_plan, observations)
            except Exception:
                pass

        return self._revise_with_rules(current_plan, observations, new_plan_id)

    def _revise_with_llm(self, current_plan: PlanTree, observations: List[Any]) -> PlanTree:
        """Revise plan using LLM."""
        import litellm

        obs_str = json.dumps(
            [
                {
                    "node_id": getattr(obs, "node_id", "unknown"),
                    "success": getattr(obs, "success", False),
                    "error": getattr(obs, "error", None),
                    "result": getattr(obs, "result", None),
                }
                for obs in observations
            ],
            ensure_ascii=False,
        )

        prompt = PLAN_REVISION_PROMPT.format(
            original_plan=current_plan.json(),
            observations=obs_str,
            context="{}",
        )

        response = litellm.completion(
            model=f"{self.config.provider}/{self.config.model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        content = response.choices[0].message.content
        plan_data = self._parse_llm_response(content)

        new_plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        root_node = self._build_node_from_llm_output(plan_data.get("plan_tree", plan_data))

        current_plan.add_revision("LLM-based revision", new_plan_id)

        return PlanTree(
            id=new_plan_id,
            root=root_node,
            confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=new_plan_id, root=root_node)),
        )

    def _revise_with_rules(self, current_plan: PlanTree, observations: List[Any], new_plan_id: str) -> PlanTree:
        """Rule-based plan revision fallback."""
        current_plan.add_revision("Rule-based revision", new_plan_id)

        failed_nodes = [obs for obs in observations if hasattr(obs, "success") and not obs.success]

        goal = current_plan.root.content
        revised_root = self._generate_with_rules(goal, {})

        if failed_nodes:
            retry_node = PlanNode(
                id=f"node-{uuid.uuid4().hex[:8]}",
                type="action",
                content=f"重试 {len(failed_nodes)} 个失败操作",
                priority=0,
                confidence=0.6,
            )
            revised_root.children = [retry_node] + revised_root.children

        return PlanTree(
            id=new_plan_id,
            root=revised_root,
            confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=new_plan_id, root=revised_root)),
        )

    def generate_plan_stream(self, goal: str, context: Dict[str, Any]) -> Any:
        """
        Generate a plan with streaming (returns plan incrementally).

        Args:
            goal: User goal
            context: Context

        Yields:
            Partial plan updates as they're generated
        """
        if not self._llm_available or not self.config:
            # Fallback: yield the full plan at once
            yield self.generate_plan(goal, context)
            return

        import litellm

        context_str = json.dumps(
            {
                "history": context.get("history", []),
                "available_tools": context.get("available_tools", []),
            },
            ensure_ascii=False,
        )

        prompt = PLAN_GENERATION_PROMPT.format(context=context_str, goal=goal)

        response = litellm.completion(
            model=f"{self.config.provider}/{self.config.model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
            stream=True,
        )

        accumulated = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                accumulated += chunk.choices[0].delta.content
                yield {"type": "chunk", "content": chunk.choices[0].delta.content}

        # Yield the final parsed plan
        try:
            plan_data = self._parse_llm_response(accumulated)
            plan_id = f"plan-{uuid.uuid4().hex[:8]}"
            root_node = self._build_node_from_llm_output(plan_data.get("plan_tree", plan_data))
            plan = PlanTree(
                id=plan_id,
                root=root_node,
                confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=plan_id, root=root_node)),
            )
            yield {"type": "plan", "plan": plan}
        except Exception:
            yield {"type": "error", "message": "Failed to parse streaming plan output"}
