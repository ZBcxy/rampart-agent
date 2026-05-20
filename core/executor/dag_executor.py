import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """
    执行结果
    """

    node_id: str = Field(..., description="节点ID")
    success: bool = Field(..., description="执行是否成功")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(0.0, description="执行时间（秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="执行时间戳")


class DAGExecutor:
    """
    DAG 执行器
    负责执行有向无环图
    """

    def __init__(self, sandbox_manager=None):
        self.sandbox_manager = sandbox_manager
        self.execution_cache = {}

    async def execute_dag(self, dag: Dict[str, Any], context: Dict[str, Any]) -> List[ExecutionResult]:
        """
        执行 DAG

        Args:
            dag: DAG 图结构
            context: 上下文信息

        Returns:
            List[ExecutionResult]: 所有节点的执行结果
        """
        results = []
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])

        # 构建依赖关系
        dependencies = self._build_dependency_graph(nodes, edges)

        # 按拓扑顺序执行
        execution_order = self._topological_sort(nodes, dependencies)

        # 并行执行无依赖的节点
        for level in execution_order:
            tasks = []
            for node_id in level:
                node = self._find_node_by_id(nodes, node_id)
                if node:
                    tasks.append(self._execute_node(node, context, results))

            if tasks:
                level_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in level_results:
                    if isinstance(res, ExecutionResult):
                        results.append(res)

        return results

    def _build_dependency_graph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        构建依赖关系图

        Args:
            nodes: 节点列表
            edges: 边列表

        Returns:
            Dict[str, List[str]]: 节点到依赖节点的映射
        """
        dependencies = {node["id"]: [] for node in nodes}

        for edge in edges:
            from_node = edge.get("from")
            to_node = edge.get("to")
            if from_node and to_node:
                dependencies[to_node].append(from_node)

        return dependencies

    def _topological_sort(self, nodes: List[Dict[str, Any]], dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """
        拓扑排序，返回分层执行顺序

        Args:
            nodes: 节点列表
            dependencies: 依赖关系

        Returns:
            List[List[str]]: 分层执行顺序
        """
        in_degree = {node["id"]: len(dependencies[node["id"]]) for node in nodes}
        order = []

        # 找到所有入度为0的节点
        current_level = [node["id"] for node in nodes if in_degree[node["id"]] == 0]

        while current_level:
            order.append(current_level.copy())
            next_level = []

            for node_id in current_level:
                # 找到所有依赖此节点的节点
                for edge in [e for e in dependencies if node_id in dependencies[e]]:
                    in_degree[edge] -= 1
                    if in_degree[edge] == 0:
                        next_level.append(edge)

            current_level = next_level

        return order

    def _find_node_by_id(self, nodes: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID查找节点

        Args:
            nodes: 节点列表
            node_id: 节点ID

        Returns:
            Optional[Dict[str, Any]]: 节点信息
        """
        for node in nodes:
            if node["id"] == node_id:
                return node
        return None

    async def _execute_node(
        self, node: Dict[str, Any], context: Dict[str, Any], previous_results: List[ExecutionResult]
    ) -> ExecutionResult:
        """
        执行单个节点

        Args:
            node: 节点信息
            context: 上下文信息
            previous_results: 之前的执行结果

        Returns:
            ExecutionResult: 执行结果
        """
        start_time = datetime.now()

        try:
            result = await self._execute_node_content(node, context, previous_results)
            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(node_id=node["id"], success=True, result=result, execution_time=execution_time)

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(node_id=node["id"], success=False, error=str(e), execution_time=execution_time)

    async def _execute_node_content(
        self, node: Dict[str, Any], context: Dict[str, Any], previous_results: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """
        执行节点内容

        Args:
            node: 节点信息
            context: 上下文信息
            previous_results: 之前的执行结果

        Returns:
            Dict[str, Any]: 执行结果
        """
        node_type = node.get("type", "action")
        tool_id = node.get("tool_id")

        if node_type == "action" and tool_id:
            return await self._execute_tool(tool_id, context)
        elif node_type == "parallel":
            return await self._execute_parallel(node, context)
        elif node_type == "branch":
            return await self._execute_branch(node, context, previous_results)
        elif node_type == "human":
            return await self._execute_human(node, context)
        else:
            return await self._execute_default(node, context)

    async def _execute_tool(self, tool_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_id: 工具ID
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 检查缓存
        if tool_id in self.execution_cache:
            return self.execution_cache[tool_id]

        # 执行工具
        result = {
            "tool_id": tool_id,
            "status": "completed",
            "data": context.get("input_data", {}),
            "timestamp": datetime.now().isoformat(),
        }

        # 缓存结果
        self.execution_cache[tool_id] = result

        return result

    async def _execute_parallel(self, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行并行节点

        Args:
            node: 节点信息
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        return {"type": "parallel", "status": "completed", "message": "并行执行完成"}

    async def _execute_branch(
        self, node: Dict[str, Any], context: Dict[str, Any], previous_results: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """
        执行分支节点

        Args:
            node: 节点信息
            context: 上下文信息
            previous_results: 之前的执行结果

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 简化实现：选择第一个分支
        return {"type": "branch", "status": "completed", "selected_branch": 0}

    async def _execute_human(self, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行人工节点

        Args:
            node: 节点信息
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        return {"type": "human", "status": "pending", "message": "等待人工确认"}

    async def _execute_default(self, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行默认节点

        Args:
            node: 节点信息
            context: 上下文信息

        Returns:
            Dict[str, Any]: 执行结果
        """
        return {"status": "completed", "content": node.get("content", "")}

    def clear_cache(self):
        """
        清除执行缓存
        """
        self.execution_cache.clear()
