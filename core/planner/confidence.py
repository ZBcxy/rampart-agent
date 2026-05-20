import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from .models import PlanNode, PlanTree


class ConfidenceEvaluator:
    """
    置信度评估器
    负责评估计划的置信度分数
    """

    def __init__(self):
        # 工具使用历史记录
        self.tool_success_history: Dict[str, List[bool]] = defaultdict(list)
        # 任务完成历史
        self.task_completion_history: List[Tuple[str, bool]] = []
        # 缓存的置信度评估结果
        self._confidence_cache: Dict[str, float] = {}
        # 常见高成功任务模式
        self.high_success_patterns = [
            r"分析.*数据",
            r"生成.*报告",
            r"创建.*文档",
            r"查询.*信息",
            r"搜索.*内容",
        ]
        # 常见高风险模式
        self.high_risk_patterns = [
            r"delete|rm|remove|destroy|drop|erase",
            r"payment|transfer|transaction|buy|purchase",
            r"install|download|execute|run",
        ]

    def evaluate_plan(self, plan: PlanTree) -> float:
        """
        评估整个计划的置信度

        Args:
            plan: 计划树

        Returns:
            float: 置信度分数（0-1）
        """
        if not plan.root:
            return 0.0

        # 检查缓存
        cache_key = f"{plan.id}_{plan.created_at.isoformat()}"
        if cache_key in self._confidence_cache:
            return self._confidence_cache[cache_key]

        # 多因素评估
        node_confidence = self._evaluate_node(plan.root)
        factors = self.analyze_confidence_factors(plan)

        # 加权计算总置信度
        total_confidence = (
            node_confidence * 0.4
            + factors["node_complexity"] * 0.15
            + factors["tool_familiarity"] * 0.2
            + factors["context_relevance"] * 0.15
            + factors["execution_risk"] * 0.1
        )

        result = min(max(total_confidence, 0.0), 1.0)
        self._confidence_cache[cache_key] = result

        return result

    def _evaluate_node(self, node: PlanNode) -> float:
        """
        递归评估节点置信度

        Args:
            node: 计划节点

        Returns:
            float: 节点置信度
        """
        if not node.children:
            return node.confidence

        # 根据节点类型计算置信度
        if node.type == "parallel":
            # 并行节点：取所有子节点的平均置信度，同时考虑并行执行风险
            child_confidences = [self._evaluate_node(child) for child in node.children]
            avg_conf = sum(child_confidences) / len(child_confidences) if child_confidences else 0.0
            return avg_conf * 0.9  # 并行增加10%复杂度风险

        elif node.type == "branch":
            # 分支节点：取最高置信度分支，同时考虑分支选择的不确定性
            child_confidences = [self._evaluate_node(child) for child in node.children]
            max_conf = max(child_confidences) if child_confidences else 0.0
            return max_conf * 0.85  # 分支选择增加15%不确定性

        else:
            # 动作或人工节点：取所有子节点的最低置信度（串联）
            child_confidences = [self._evaluate_node(child) for child in node.children]
            if not child_confidences:
                return node.confidence

            min_child_conf = min(child_confidences)
            return min(node.confidence, min_child_conf) * 0.95  # 串联有5%累计风险

    def analyze_confidence_factors(self, plan: PlanTree) -> Dict[str, float]:
        """
        分析影响置信度的因素

        Args:
            plan: 计划树

        Returns:
            Dict[str, float]: 各因素及其影响权重
        """
        factors = {
            "node_complexity": self._calculate_complexity_factor(plan),
            "tool_familiarity": self._calculate_familiarity_factor(plan),
            "context_relevance": self._calculate_context_factor(plan),
            "execution_risk": self._calculate_risk_factor(plan),
        }

        return factors

    def _calculate_complexity_factor(self, plan: PlanTree) -> float:
        """计算复杂度因素（更智能的评估）"""
        node_count = self._count_nodes(plan.root)
        max_depth = self._calculate_depth(plan.root)

        # 考虑节点数量和深度的复合复杂度
        complexity_score = node_count * 0.6 + max_depth * 0.4

        # 复杂度在合理范围内时置信度高
        if complexity_score < 10:
            return 1.0
        elif complexity_score < 30:
            return max(0.6, 1.0 - complexity_score / 100.0)
        elif complexity_score < 100:
            return max(0.3, 1.0 - complexity_score / 150.0)
        else:
            return 0.1

    def _calculate_familiarity_factor(self, plan: PlanTree) -> float:
        """计算工具熟悉度因素（基于历史数据）"""
        tools = self._extract_tools(plan.root)
        if not tools:
            return 0.7  # 默认中等熟悉度

        total_score = 0.0
        for tool in tools:
            history = self.tool_success_history.get(tool, [])
            if not history:
                total_score += 0.7  # 未知工具给中等分数
            else:
                success_rate = sum(history) / len(history)
                total_score += success_rate

        avg_score = total_score / len(tools)
        return avg_score

    def _calculate_context_factor(self, plan: PlanTree) -> float:
        """计算上下文相关性因素（基于历史模式匹配）"""
        content = plan.root.content.lower()

        # 检查是否匹配常见高成功率模式
        for pattern in self.high_success_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 0.95

        # 检查任务完成历史中的相似任务
        similar_task_count = 0
        for task_desc, success in self.task_completion_history:
            if any(keyword in content and keyword in task_desc.lower() for keyword in content.split()):
                similar_task_count += 1

        if similar_task_count >= 3:
            return 0.85
        elif similar_task_count >= 1:
            return 0.75

        return 0.6  # 默认相关性

    def _calculate_risk_factor(self, plan: PlanTree) -> float:
        """计算执行风险因素（更详细的风险评估）"""
        risk_score = self._assess_risk(plan.root)

        # 风险越低，置信度越高
        return 1.0 - risk_score

    def _count_nodes(self, node: PlanNode) -> int:
        """递归计算节点数量"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _calculate_depth(self, node: PlanNode) -> int:
        """计算计划树的最大深度"""
        if not node.children:
            return 1
        return 1 + max(self._calculate_depth(child) for child in node.children)

    def _extract_tools(self, node: PlanNode) -> Set[str]:
        """从计划中提取使用的工具"""
        tools = set()

        # 从节点内容中提取工具ID
        if hasattr(node, "tool_id") and node.tool_id:
            tools.add(node.tool_id)

        # 从内容中提取工具引用
        content = node.content.lower()
        tool_pattern = r"tool_(\w+)|using (\w+)"
        matches = re.findall(tool_pattern, content)
        for match in matches:
            tool_name = match[0] or match[1]
            tools.add(tool_name)

        for child in node.children:
            tools.update(self._extract_tools(child))

        return tools

    def _assess_risk(self, node: PlanNode) -> float:
        """评估节点风险等级（更全面的风险分析）"""
        risk = 0.0
        content = node.content.lower()

        # 检查高风险关键词
        for pattern in self.high_risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                risk += 0.25

        # 检查节点类型风险
        if node.type == "human":
            risk += 0.1  # 人工节点有延迟风险
        elif node.type == "branch":
            risk += 0.05  # 分支选择有不确定性

        # 检查置信度低于阈值的风险
        if node.confidence < 0.5:
            risk += 0.2

        # 递归评估子节点，取最大风险
        for child in node.children:
            child_risk = self._assess_risk(child)
            if child_risk > risk:
                risk = child_risk

        return min(risk, 1.0)

    def is_confidence_sufficient(self, plan: PlanTree, threshold: float = 0.5) -> bool:
        """
        判断置信度是否足够

        Args:
            plan: 计划树
            threshold: 置信度阈值

        Returns:
            bool: 是否满足阈值要求
        """
        return self.evaluate_plan(plan) >= threshold

    def record_tool_execution(self, tool_id: str, success: bool):
        """
        记录工具执行结果，用于后续置信度计算

        Args:
            tool_id: 工具ID
            success: 是否成功
        """
        self.tool_success_history[tool_id].append(success)
        # 保持最近100次记录
        if len(self.tool_success_history[tool_id]) > 100:
            self.tool_success_history[tool_id] = self.tool_success_history[tool_id][-100:]

    def record_task_completion(self, task_desc: str, success: bool):
        """
        记录任务完成结果

        Args:
            task_desc: 任务描述
            success: 是否成功
        """
        self.task_completion_history.append((task_desc, success))
        if len(self.task_completion_history) > 50:
            self.task_completion_history = self.task_completion_history[-50:]

    def clear_cache(self):
        """清除缓存的置信度评估结果"""
        self._confidence_cache.clear()

    def get_execution_statistics(self) -> Dict[str, any]:
        """获取执行统计数据"""
        total_tool_executions = sum(len(history) for history in self.tool_success_history.values())
        total_task_executions = len(self.task_completion_history)
        avg_tool_success = (
            sum(sum(history) / len(history) for history in self.tool_success_history.values() if history)
            / len(self.tool_success_history)
            if self.tool_success_history
            else 0
        )
        avg_task_success = (
            sum(1 for _, success in self.task_completion_history if success) / total_task_executions
            if total_task_executions > 0
            else 0
        )

        return {
            "total_tool_executions": total_tool_executions,
            "total_task_executions": total_task_executions,
            "average_tool_success_rate": avg_tool_success,
            "average_task_success_rate": avg_task_success,
            "tracked_tools": list(self.tool_success_history.keys()),
        }
