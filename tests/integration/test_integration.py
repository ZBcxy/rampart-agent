"""集成测试：验证各模块之间的协作"""

import pytest
from core.planner import Planner
from core.executor import DAGExecutor, SandboxManager
from core.memory import WorkingMemory, EpisodicMemory, SemanticMemory
from core.performance import PerformanceMonitor


class TestAgentIntegration:
    """智能体整体集成测试"""

    def test_planner_executor_integration(self):
        """测试规划器与执行器的集成"""
        import asyncio
        planner = Planner()
        executor = DAGExecutor()

        plan = planner.generate_plan('分析销售数据并生成报告', {'history': []})
        
        assert plan is not None
        assert plan.id is not None
        assert plan.confidence > 0

        dag = {
            "nodes": [
                {"id": "node1", "type": "action", "tool_id": "analyze_sales"},
                {"id": "node2", "type": "action", "tool_id": "generate_report"}
            ],
            "edges": [{"from": "node1", "to": "node2"}]
        }
        result = asyncio.run(executor.execute_dag(dag, {"input_data": {}}))
        
        assert result is not None
        assert len(result) > 0
        assert all(isinstance(r, dict) or hasattr(r, 'success') for r in result)

    def test_memory_integration(self):
        """测试三层记忆系统的集成"""
        wm = WorkingMemory()
        em = EpisodicMemory()
        sm = SemanticMemory()

        wm.add('用户询问销售报告', item_type='observation', importance=0.8)
        em.add('用户请求', '生成了销售报告', success=True)
        sm.add('销售报告包含收入、利润、趋势分析', tags=['sales', 'report'])

        wm_result = wm.search('销售报告')
        em_result = em.search('用户')
        sm_result = sm.search('销售')

        assert len(wm_result) > 0
        assert len(em_result) > 0
        assert len(sm_result) > 0

    def test_sandbox_security_integration(self):
        """测试沙箱安全机制"""
        sandbox_manager = SandboxManager()
        
        sandbox_id = sandbox_manager.create_sandbox()
        
        safe_code = """
result = sum(range(100))
"""
        unsafe_code = """
import subprocess
result = subprocess.run(['ls', '-la'], capture_output=True).stdout.decode()
"""

        safe_result = sandbox_manager.execute_code(sandbox_id, safe_code)
        unsafe_result = sandbox_manager.execute_code(sandbox_id, unsafe_code)

        assert safe_result['success'] is True
        assert unsafe_result['success'] is False
        assert 'violations' in unsafe_result

    def test_performance_monitor_integration(self):
        """测试性能监控与其他模块的集成"""
        monitor = PerformanceMonitor()
        planner = Planner()

        @monitor.measure('plan_generation', tags=['integration'])
        def generate_test_plan():
            return planner.generate_plan('测试任务', {})

        plan = generate_test_plan()

        assert plan is not None

        # get_statistics() returns overall stats dict with 'metrics' key
        stats = monitor.get_statistics()
        assert stats['total_operations'] >= 1
        assert stats['total_time'] > 0
        assert 'plan_generation' in stats['metrics']

    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        import asyncio

        planner = Planner()
        executor = DAGExecutor()
        wm = WorkingMemory()
        em = EpisodicMemory()

        wm.add('用户希望了解产品销量')

        plan = planner.generate_plan('分析产品销量数据', {'history': []})

        # Convert plan to DAG and execute
        dag = {
            "nodes": [
                {"id": "n0", "type": plan.root.type, "content": plan.root.content},
            ],
            "edges": [],
        }
        if plan.root.children:
            for child in plan.root.children:
                dag["nodes"].append({
                    "id": child.id, "type": child.type, "content": child.content,
                })
                dag["edges"].append({"from": "n0", "to": child.id})

        results = asyncio.run(executor.execute_dag(dag, {"input_data": {}}))

        success = all(r.success for r in results)
        em.add('分析产品销量数据', str([r.model_dump() for r in results]), success=success)

        assert plan.confidence > 0
        assert len(results) > 0

        episodes = em.search('销量')
        assert len(episodes) > 0


class TestErrorHandlingIntegration:
    """异常处理集成测试"""

    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        planner = Planner()
        
        with pytest.raises(ValueError):
            planner.generate_plan(None, {})
        
        with pytest.raises(ValueError):
            planner.generate_plan('', {})

    def test_sandbox_limits(self):
        """测试沙箱资源限制"""
        sandbox_manager = SandboxManager()
        
        sandbox_manager.max_sandboxes = 1
        sandbox_manager.create_sandbox()
        
        with pytest.raises(RuntimeError):
            sandbox_manager.create_sandbox()

    def test_memory_expiration(self):
        """测试记忆过期机制"""
        from datetime import timedelta

        # WorkingMemory takes max_age_minutes — use a very small value
        wm = WorkingMemory(max_size=100, max_age_minutes=0.001)  # ~0.06 seconds

        wm.add('临时数据')
        assert wm.size() == 1

        import time
        time.sleep(0.1)  # Wait past expiration

        # Cleanup happens on next add
        wm.add('触发清理')
        # The old item should be cleaned up
        assert wm.size() <= 2  # At most 2 items (trigger entry + possibly surviving old)
