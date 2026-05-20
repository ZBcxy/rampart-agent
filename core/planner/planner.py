import uuid
from typing import Any, Dict

from .confidence import ConfidenceEvaluator
from .models import PlanNode, PlanTree
from .ooda_loop import OODALoop


class Planner:
    """
    主规划器
    负责生成和修订执行计划
    """

    def __init__(self):
        self.confidence_evaluator = ConfidenceEvaluator()
        self.ooda_loop = OODALoop(self)

    def generate_plan(self, goal: str, context: Dict[str, Any]) -> PlanTree:
        """
        根据目标和上下文生成执行计划

        Args:
            goal: 用户目标描述（自然语言）
            context: 当前上下文信息，包含任务历史、可用工具等

        Returns:
            PlanTree: 生成的执行计划树，包含置信度评分

        Raises:
            ValueError: 当目标无效或上下文不完整时
        """
        if not goal or not isinstance(goal, str):
            raise ValueError("目标必须是有效的字符串")

        if context is None:
            context = {}

        # 生成唯一计划ID
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        # 构建计划树（简化实现，实际应调用LLM生成）
        root_node = self._build_plan_structure(goal, context)

        # 评估置信度
        plan = PlanTree(
            id=plan_id,
            root=root_node,
            confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=plan_id, root=root_node)),
        )

        return plan

    def _build_plan_structure(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        构建计划结构（简化实现）

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            PlanNode: 计划树根节点
        """
        # 简单示例：根据目标类型生成不同的计划结构
        if "分析" in goal or "报告" in goal:
            return self._build_analysis_plan(goal, context)
        elif "创建" in goal or "生成" in goal:
            return self._build_creation_plan(goal, context)
        else:
            return self._build_default_plan(goal, context)

    def _build_analysis_plan(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        构建分析类型的计划

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            PlanNode: 计划树根节点
        """
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content=f"分析任务: {goal}", priority=1, confidence=0.85
        )

        # 添加子节点
        data_collection = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="收集相关数据", priority=2, confidence=0.9
        )

        analysis = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="执行数据分析", priority=3, confidence=0.8
        )

        report = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="生成分析报告", priority=4, confidence=0.85
        )

        root.children = [data_collection, analysis, report]
        return root

    def _build_creation_plan(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        构建创建类型的计划

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            PlanNode: 计划树根节点
        """
        root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content=f"创建任务: {goal}", priority=1, confidence=0.8
        )

        planning = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="规划创建步骤", priority=2, confidence=0.9
        )

        execution = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="执行创建操作", priority=3, confidence=0.75
        )

        verification = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="验证创建结果", priority=4, confidence=0.9
        )

        root.children = [planning, execution, verification]
        return root

    def _build_default_plan(self, goal: str, context: Dict[str, Any]) -> PlanNode:
        """
        构建默认计划

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            PlanNode: 计划树根节点
        """
        return PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content=f"执行任务: {goal}", priority=1, confidence=0.7
        )

    def revise_plan(self, current_plan: PlanTree, observations: Any) -> PlanTree:
        """
        根据执行结果修订计划

        Args:
            current_plan: 当前计划
            observations: 观察结果

        Returns:
            PlanTree: 修订后的计划
        """
        # 生成新的计划ID
        new_plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        # 创建修订记录
        current_plan.add_revision("执行观察结果触发修订", new_plan_id)

        # 分析失败的节点并生成修正计划
        if isinstance(observations, list):
            failed_nodes = [obs for obs in observations if hasattr(obs, "success") and not obs.success]
            if failed_nodes:
                return self._repair_failed_nodes(current_plan, failed_nodes)

        # 默认：创建一个调整后的计划
        revised_root = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}",
            type="action",
            content=f"修订计划: {current_plan.root.content}",
            priority=1,
            confidence=min(current_plan.confidence + 0.05, 1.0),
        )

        return PlanTree(
            id=new_plan_id,
            root=revised_root,
            confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=new_plan_id, root=revised_root)),
        )

    def _repair_failed_nodes(self, plan: PlanTree, failed_nodes: list) -> PlanTree:
        """
        修复失败的节点

        Args:
            plan: 当前计划
            failed_nodes: 失败节点列表

        Returns:
            PlanTree: 修复后的计划
        """
        new_plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        # 简化实现：重新生成计划
        goal = plan.root.content
        revised_root = self._build_plan_structure(goal, {})

        # 增加重试节点
        retry_node = PlanNode(
            id=f"node-{uuid.uuid4().hex[:8]}", type="action", content="重试失败操作", priority=1, confidence=0.6
        )

        revised_root.children = [retry_node] + revised_root.children

        return PlanTree(
            id=new_plan_id,
            root=revised_root,
            confidence=self.confidence_evaluator.evaluate_plan(PlanTree(id=new_plan_id, root=revised_root)),
        )

    def execute_with_ooda(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 OODA 循环执行计划

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        return self.ooda_loop.execute(goal, context)

    def evaluate_plan_confidence(self, plan: PlanTree) -> float:
        """
        评估计划置信度

        Args:
            plan: 计划树

        Returns:
            float: 置信度分数
        """
        return self.confidence_evaluator.evaluate_plan(plan)
