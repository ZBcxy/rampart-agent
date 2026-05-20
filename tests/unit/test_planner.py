import pytest
from core.planner import Planner, PlanTree, PlanNode
from core.planner.confidence import ConfidenceEvaluator


class TestPlanner:
    def test_generate_plan_with_valid_goal(self):
        planner = Planner()
        goal = "分析销售数据并生成报告"
        context = {"history": []}
        
        plan = planner.generate_plan(goal, context)
        
        assert isinstance(plan, PlanTree)
        assert plan.id is not None
        assert plan.root is not None
        assert 0 <= plan.confidence <= 1.0

    def test_generate_plan_with_invalid_goal(self):
        planner = Planner()
        
        with pytest.raises(ValueError):
            planner.generate_plan(None, {})
        
        with pytest.raises(ValueError):
            planner.generate_plan("", {})

    def test_generate_plan_with_empty_context(self):
        planner = Planner()
        goal = "完成任务A"
        
        plan = planner.generate_plan(goal, None)
        
        assert plan is not None
        assert plan.root is not None

    def test_plan_revision(self):
        planner = Planner()
        goal = "测试计划修订"
        context = {"history": []}
        
        plan = planner.generate_plan(goal, context)
        revised_plan = planner.revise_plan(plan, "需要更详细的步骤")
        
        assert isinstance(revised_plan, PlanTree)
        assert revised_plan.root.content != plan.root.content


class TestConfidenceEvaluator:
    def test_evaluate_plan(self):
        evaluator = ConfidenceEvaluator()
        node = PlanNode(id="test-node", type="action", content="测试节点")
        plan = PlanTree(id="test-plan", root=node, confidence=0.7)
        
        confidence = evaluator.evaluate_plan(plan)
        
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1.0

    def test_calculate_context_factor(self):
        evaluator = ConfidenceEvaluator()
        node = PlanNode(id="test-node", type="action", content="分析销售数据")
        plan = PlanTree(id="test-plan", root=node, confidence=0.7)
        
        relevance = evaluator._calculate_context_factor(plan)
        
        assert isinstance(relevance, float)
        assert 0 <= relevance <= 1.0