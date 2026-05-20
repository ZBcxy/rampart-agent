import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolBlueprint(BaseModel):
    """
    工具蓝图定义
    """

    tool_id: str = Field(..., description="工具唯一标识")
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    type: str = Field(..., description="工具类型（python_code, api, etc.）")
    code: Optional[str] = Field(None, description="工具代码")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="输入参数 schema")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="输出参数 schema")
    confidence: float = Field(0.5, description="置信度")
    timeout_seconds: int = Field(30, description="超时时间")
    requires_sandbox: bool = Field(False, description="是否需要沙箱")


class ToolMatchResult(BaseModel):
    """
    工具匹配结果
    """

    tool_blueprint: ToolBlueprint
    match_score: float = Field(0.0, description="匹配分数")
    execution_cost: float = Field(0.0, description="执行成本")
    estimated_delay: float = Field(0.0, description="预估延迟")


class ToolWeaver:
    """
    工具编织器
    负责根据能力描述匹配工具并生成执行图
    """

    def __init__(self):
        self.static_tools = {}
        self.dynamic_tools = {}

    def register_static_tool(self, blueprint: ToolBlueprint):
        """
        注册静态工具

        Args:
            blueprint: 工具蓝图
        """
        self.static_tools[blueprint.tool_id] = blueprint

    def create_dynamic_tool(self, blueprint: ToolBlueprint) -> str:
        """
        创建动态工具

        Args:
            blueprint: 工具蓝图

        Returns:
            str: 动态工具ID
        """
        dynamic_id = f"dynamic-{uuid.uuid4().hex[:8]}"
        blueprint.tool_id = dynamic_id
        self.dynamic_tools[dynamic_id] = blueprint
        return dynamic_id

    def match_tools(self, capability_description: str, context: Dict[str, Any]) -> List[ToolMatchResult]:
        """
        根据能力描述匹配工具

        Args:
            capability_description: 能力描述
            context: 上下文信息

        Returns:
            List[ToolMatchResult]: 匹配结果列表（按优先级排序）
        """
        results = []

        # 匹配静态工具
        for tool_id, blueprint in self.static_tools.items():
            score = self._calculate_match_score(capability_description, blueprint)
            if score > 0.3:
                results.append(
                    ToolMatchResult(
                        tool_blueprint=blueprint,
                        match_score=score,
                        execution_cost=self._estimate_cost(blueprint),
                        estimated_delay=self._estimate_delay(blueprint),
                    )
                )

        # 如果没有找到合适的静态工具，考虑生成动态工具
        if not results or max(r.match_score for r in results) < 0.7:
            dynamic_blueprint = self._generate_dynamic_tool(capability_description, context)
            if dynamic_blueprint:
                results.append(
                    ToolMatchResult(
                        tool_blueprint=dynamic_blueprint, match_score=0.85, execution_cost=0.5, estimated_delay=2.0
                    )
                )

        # 按匹配分数排序
        results.sort(key=lambda x: (-x.match_score, x.execution_cost, x.estimated_delay))

        return results

    def _calculate_match_score(self, capability: str, blueprint: ToolBlueprint) -> float:
        """
        计算工具匹配分数

        Args:
            capability: 能力描述
            blueprint: 工具蓝图

        Returns:
            float: 匹配分数（0-1）
        """
        score = 0.0

        # 检查名称匹配
        if blueprint.name.lower() in capability.lower():
            score += 0.3

        # 检查描述匹配
        if blueprint.description.lower() in capability.lower():
            score += 0.4

        # 检查关键词匹配
        capability_words = set(capability.lower().split())
        description_words = set(blueprint.description.lower().split())
        overlap = capability_words & description_words
        if overlap:
            score += min(len(overlap) * 0.1, 0.3)

        return min(score, 1.0)

    def _estimate_cost(self, blueprint: ToolBlueprint) -> float:
        """
        估算执行成本

        Args:
            blueprint: 工具蓝图

        Returns:
            float: 成本估计
        """
        # 简化实现
        if blueprint.requires_sandbox:
            return 0.8
        return 0.2

    def _estimate_delay(self, blueprint: ToolBlueprint) -> float:
        """
        估算执行延迟

        Args:
            blueprint: 工具蓝图

        Returns:
            float: 延迟估计（秒）
        """
        return blueprint.timeout_seconds / 3.0

    def _generate_dynamic_tool(self, capability: str, context: Dict[str, Any]) -> Optional[ToolBlueprint]:
        """
        生成动态工具蓝图

        Args:
            capability: 能力描述
            context: 上下文信息

        Returns:
            Optional[ToolBlueprint]: 生成的工具蓝图
        """
        # 简化实现：创建一个占位的动态工具蓝图
        return ToolBlueprint(
            tool_id=f"dynamic-{uuid.uuid4().hex[:8]}",
            name=f"动态工具: {capability[:30]}...",
            description=f"根据能力描述动态生成的工具: {capability}",
            type="python_code",
            code="# 动态生成的代码将在此处",
            confidence=0.85,
            timeout_seconds=30,
            requires_sandbox=True,
        )

    def weave_execution_graph(self, plan_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将工具调用编织成执行图

        Args:
            plan_nodes: 计划节点列表

        Returns:
            Dict[str, Any]: 执行图（DAG）
        """
        graph = {"nodes": [], "edges": [], "entry_point": None, "exit_point": None}

        for i, node in enumerate(plan_nodes):
            node_id = f"node-{i}"
            graph["nodes"].append(
                {
                    "id": node_id,
                    "type": node.get("type", "action"),
                    "content": node.get("content", ""),
                    "tool_id": node.get("tool_id"),
                    "dependencies": node.get("dependencies", []),
                }
            )

            # 添加边
            if i > 0:
                graph["edges"].append({"from": f"node-{i - 1}", "to": node_id})

        if graph["nodes"]:
            graph["entry_point"] = "node-0"
            graph["exit_point"] = f"node-{len(plan_nodes) - 1}"

        return graph
