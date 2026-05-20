from datetime import datetime
from typing import Any, Dict, List

from .confidence import ConfidenceEvaluator
from .models import ExecutionObservation, PlanTree


class OODALoop:
    """
    OODA 循环实现
    Observe -> Orient -> Decide -> Act
    """

    def __init__(self, planner):
        self.planner = planner
        self.confidence_evaluator = ConfidenceEvaluator()
        self.MAX_REVISIONS = 5
        self.DEVIATION_THRESHOLD = 0.3
        self.CONFIDENCE_THRESHOLD = 0.5

    def execute(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整的 OODA 循环

        Args:
            goal: 用户目标
            context: 上下文信息

        Returns:
            Dict[str, Any]: 最终执行结果
        """
        # 初始计划生成
        current_plan = self.planner.generate_plan(goal, context)
        revision_count = 0

        while revision_count < self.MAX_REVISIONS:
            # Act: 执行当前计划
            observations = self._execute_plan(current_plan, context)

            # Observe: 观察执行结果
            deviations = self._observe(observations)

            if not deviations:
                # 执行成功，返回结果
                return self._aggregate_results(observations)

            # Orient: 判断是否需要重规划
            action = self._orient(deviations, current_plan)

            if action == "continue":
                # 偏差可接受，继续执行
                return self._aggregate_results(observations)

            elif action == "adjust":
                # 需要调整计划
                current_plan = self.planner.revise_plan(current_plan, observations)
                revision_count += 1

            elif action == "replan":
                # 需要重新规划
                current_plan = self.planner.generate_plan(goal, context)
                revision_count += 1

            elif action == "human":
                # 需要人工介入
                return {
                    "status": "pending_human",
                    "message": "需要人工介入确认",
                    "observations": [obs.dict() for obs in observations],
                    "plan": current_plan.dict(),
                }

        # 超过最大修订次数
        return {
            "status": "failed",
            "message": f"超过最大修订次数 ({self.MAX_REVISIONS})",
            "observations": [obs.dict() for obs in observations],
        }

    def _execute_plan(self, plan: PlanTree, context: Dict[str, Any]) -> List[ExecutionObservation]:
        """
        执行计划，收集观察结果

        Args:
            plan: 计划树
            context: 上下文信息

        Returns:
            List[ExecutionObservation]: 观察结果列表
        """
        observations = []

        def execute_node(node, parent_context):
            observation = ExecutionObservation(node_id=node.id, success=True, result=None, error=None, deviation=0.0)

            try:
                # 模拟执行节点
                if node.type == "action":
                    result = self._execute_action(node.content, parent_context)
                    observation.result = result
                    observation.deviation = self._calculate_deviation(result, node)

                elif node.type == "branch":
                    # 根据条件选择分支
                    branch_index = self._select_branch(node, parent_context)
                    if branch_index < len(node.children):
                        execute_node(node.children[branch_index], parent_context)

                elif node.type == "parallel":
                    # 并行执行所有子节点
                    for child in node.children:
                        execute_node(child, parent_context)

                elif node.type == "human":
                    # 人工节点，标记为需要人工确认
                    observation.success = False
                    observation.error = "需要人工确认"

            except Exception as e:
                observation.success = False
                observation.error = str(e)
                observation.deviation = 1.0

            observations.append(observation)

        execute_node(plan.root, context)
        return observations

    def _execute_action(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个动作

        Args:
            action: 动作描述
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 占位实现，实际应调用执行引擎
        return {"action": action, "status": "completed", "timestamp": datetime.now().isoformat(), "data": {}}

    def _select_branch(self, node, context: Dict[str, Any]) -> int:
        """
        选择分支路径

        Args:
            node: 分支节点
            context: 上下文信息

        Returns:
            int: 选中的分支索引
        """
        # 简单实现：选择置信度最高的分支
        if not node.children:
            return -1

        max_confidence = -1
        selected_index = 0

        for i, child in enumerate(node.children):
            if child.confidence > max_confidence:
                max_confidence = child.confidence
                selected_index = i

        return selected_index

    def _calculate_deviation(self, result: Dict[str, Any], node) -> float:
        """
        计算执行结果与预期的偏差

        Args:
            result: 执行结果
            node: 计划节点

        Returns:
            float: 偏差值（0-1）
        """
        # 简化实现，实际需要根据预期结果计算
        return 0.0

    def _observe(self, observations: List[ExecutionObservation]) -> List[ExecutionObservation]:
        """
        观察执行结果，识别偏差

        Args:
            observations: 观察结果列表

        Returns:
            List[ExecutionObservation]: 有偏差的观察结果
        """
        return [obs for obs in observations if obs.deviation > self.DEVIATION_THRESHOLD or not obs.success]

    def _orient(self, deviations: List[ExecutionObservation], plan: PlanTree) -> str:
        """
        判断偏差原因，决定是否需要重规划

        Args:
            deviations: 偏差列表
            plan: 当前计划

        Returns:
            str: 决策动作 ('continue', 'adjust', 'replan', 'human')
        """
        # 检查是否有严重错误
        critical_errors = [d for d in deviations if not d.success]
        if critical_errors:
            # 检查是否需要人工确认
            for error in critical_errors:
                if "人工确认" in str(error.error):
                    return "human"

            # 检查置信度
            confidence = self.confidence_evaluator.evaluate_plan(plan)
            if confidence < self.CONFIDENCE_THRESHOLD:
                return "replan"
            return "adjust"

        # 检查偏差程度
        max_deviation = max(d.deviation for d in deviations) if deviations else 0
        if max_deviation > 0.5:
            return "replan"
        elif max_deviation > self.DEVIATION_THRESHOLD:
            return "adjust"

        return "continue"

    def _aggregate_results(self, observations: List[ExecutionObservation]) -> Dict[str, Any]:
        """
        聚合执行结果

        Args:
            observations: 观察结果列表

        Returns:
            Dict[str, Any]: 聚合结果
        """
        success_count = sum(1 for obs in observations if obs.success)
        total_count = len(observations)

        return {
            "status": "completed",
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "observations": [obs.dict() for obs in observations],
            "summary": f"{success_count}/{total_count} 步骤执行成功",
        }
