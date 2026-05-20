import pytest
import asyncio
from core.executor import DAGExecutor, ExecutionResult
from core.executor.tool_weaver import ToolWeaver, ToolBlueprint


class TestDAGExecutor:
    def test_build_dependency_graph(self):
        executor = DAGExecutor()
        nodes = [
            {"id": "node-0", "type": "action", "content": "步骤1"},
            {"id": "node-1", "type": "action", "content": "步骤2"},
            {"id": "node-2", "type": "action", "content": "步骤3"},
        ]
        edges = [
            {"from": "node-0", "to": "node-1"},
            {"from": "node-1", "to": "node-2"},
        ]
        
        dependencies = executor._build_dependency_graph(nodes, edges)
        
        assert isinstance(dependencies, dict)
        assert "node-0" in dependencies
        assert "node-1" in dependencies
        assert "node-2" in dependencies

    def test_topological_sort(self):
        executor = DAGExecutor()
        nodes = [
            {"id": "node-0", "type": "action"},
            {"id": "node-1", "type": "action"},
            {"id": "node-2", "type": "action"},
        ]
        dependencies = {
            "node-0": [],
            "node-1": ["node-0"],
            "node-2": ["node-1"],
        }
        
        execution_order = executor._topological_sort(nodes, dependencies)
        
        assert isinstance(execution_order, list)
        assert len(execution_order) > 0

    def test_execute_dag_sync(self):
        executor = DAGExecutor()
        dag = {
            "nodes": [
                {"id": "node-0", "type": "action", "content": "测试节点"},
            ],
            "edges": [],
        }
        context = {"test": "context"}
        
        results = asyncio.run(executor.execute_dag(dag, context))
        
        assert isinstance(results, list)


class TestToolWeaver:
    def test_register_static_tool(self):
        weaver = ToolWeaver()
        blueprint = ToolBlueprint(
            tool_id="test-tool",
            name="测试工具",
            description="测试描述",
            type="python_code",
        )
        
        weaver.register_static_tool(blueprint)
        
        assert "test-tool" in weaver.static_tools

    def test_create_dynamic_tool(self):
        weaver = ToolWeaver()
        blueprint = ToolBlueprint(
            tool_id="temp",
            name="动态工具",
            description="动态描述",
            type="api",
        )
        
        dynamic_id = weaver.create_dynamic_tool(blueprint)
        
        assert dynamic_id is not None
        assert dynamic_id.startswith("dynamic-")
        assert dynamic_id in weaver.dynamic_tools

    def test_match_tools_with_static_match(self):
        weaver = ToolWeaver()
        blueprint = ToolBlueprint(
            tool_id="search-tool",
            name="搜索工具",
            description="搜索工具用于搜索信息和查询数据",
            type="api",
            confidence=0.9,
        )
        weaver.register_static_tool(blueprint)
        
        results = weaver.match_tools("我需要使用搜索工具用于搜索信息和查询数据", {})
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0].tool_blueprint.tool_id == "search-tool"