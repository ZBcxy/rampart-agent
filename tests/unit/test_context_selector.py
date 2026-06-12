"""Unit tests for the Context Selector module."""

import pytest
from core.context_selector import ContextSelector, ContextChunk, SelectedContext
from core.memory import WorkingMemory


class TestContextSelector:
    def test_select_observe_phase(self):
        wm = WorkingMemory(max_size=10)
        wm.add("Observation: File not found", item_type="observation", importance=0.8)
        wm.add("Goal: Analyze data", item_type="plan", importance=1.0)
        wm.add("Tool result: success", item_type="result", importance=0.5)

        selector = ContextSelector(working_memory=wm, tools=["file_read", "web_search"])
        result = selector.select_context(
            phase="observe",
            goal="Analyze data from file",
            memory_context={"plan_content": "Step 1: Read file", "tool_names": ["file_read"]},
            history=[{"phase": "observe", "action": "read file", "observation": "success"}],
            max_tokens=2000,
        )
        assert isinstance(result, SelectedContext)
        assert result.phase == "observe"
        assert result.total_tokens <= result.token_budget
        assert len(result.items) > 0

    def test_select_orient_phase(self):
        wm = WorkingMemory(max_size=10)
        wm.add("Synthesis: Data shows anomaly in Q3", item_type="reflection", importance=0.7)

        selector = ContextSelector(working_memory=wm, tools=["file_read", "web_search"])
        result = selector.select_context(
            phase="orient",
            goal="Understand data anomaly",
            memory_context={"plan_content": "Analyze anomaly"},
            history=[],
            max_tokens=2000,
        )
        assert result.phase == "orient"
        assert isinstance(result.decision_log, str)

    def test_select_decide_phase(self):
        wm = WorkingMemory(max_size=10)
        wm.add("Plan: Step 1 - Read, Step 2 - Process", item_type="plan", importance=0.9)

        selector = ContextSelector(working_memory=wm, tools=["file_read", "python_exec", "csv_parse"])
        result = selector.select_context(
            phase="decide",
            goal="Create a data processing pipeline",
            memory_context={
                "plan_content": "Read CSV, parse, transform, output",
                "tool_names": ["file_read", "python_exec", "csv_parse"],
            },
            history=[
                {"phase": "observe", "action": "list files", "observation": "found data.csv"},
            ],
            max_tokens=2000,
        )
        assert result.phase == "decide"
        assert len(result.items) > 0

    def test_select_act_phase(self):
        wm = WorkingMemory(max_size=10)
        selector = ContextSelector(working_memory=wm, tools=["file_read", "python_exec"])
        result = selector.select_context(
            phase="act",
            goal="Execute python code",
            memory_context={
                "plan_content": "Run analysis script",
                "tool_names": ["file_read", "python_exec"],
            },
            history=[{"phase": "decide", "action": "chose python_exec"}],
            max_tokens=2000,
        )
        assert result.phase == "act"
        # Tool list should be available
        tool_list = result.get_tool_list("")
        assert "python_exec" in tool_list or any("python_exec" in item.content for item in result.items)

    def test_token_budget_enforcement(self):
        wm = WorkingMemory(max_size=20)
        for i in range(15):
            wm.add(f"Memory item {i}: " + "data " * 50, item_type="observation")

        selector = ContextSelector(working_memory=wm, tools=[])
        result = selector.select_context(
            phase="observe",
            goal="Test",
            memory_context={"plan_content": ""},
            history=[],
            max_tokens=500,  # Small budget
        )
        assert result.total_tokens <= result.token_budget + 100  # Allow small overage
        assert result.overflow_items >= 0

    def test_empty_context(self):
        selector = ContextSelector(working_memory=None, tools=[])
        result = selector.select_context(
            phase="observe",
            goal="Test goal",
            memory_context={"plan_content": ""},
            history=[],
            max_tokens=1000,
        )
        # Should at minimum include the goal
        assert len(result.items) >= 1
        assert any(item.source == "goal" for item in result.items)

    def test_context_dict_conversion(self):
        selector = ContextSelector(working_memory=None, tools=["tool_a", "tool_b"])
        result = selector.select_context(
            phase="decide",
            goal="Test",
            memory_context={"plan_content": "Plan steps"},
            history=[],
            max_tokens=2000,
        )
        ctx_dict = result.to_context_dict()
        assert "selected_memories" in ctx_dict
        assert "relevant_tools" in ctx_dict
        assert "plan_summary" in ctx_dict
        assert "goal" in ctx_dict
        assert isinstance(ctx_dict["goal"], str)

    def test_phase_specific_weighting(self):
        """Phase weights change which sources are emphasized."""
        wm = WorkingMemory(max_size=10)
        wm.add("Memory 1: important context", item_type="observation", importance=0.9)
        wm.add("Memory 2: less relevant", item_type="result", importance=0.2)

        selector = ContextSelector(working_memory=wm, tools=["tool_a"])
        observe_result = selector.select_context(
            phase="observe", goal="Test",
            memory_context={"plan_content": "Plan", "tool_names": ["tool_a"]},
            history=[], max_tokens=2000,
        )
        orient_result = selector.select_context(
            phase="orient", goal="Test",
            memory_context={"plan_content": "Plan", "tool_names": ["tool_a"]},
            history=[], max_tokens=2000,
        )
        # Both should produce valid results but with potentially different selections
        assert observe_result.phase == "observe"
        assert orient_result.phase == "orient"
        assert len(observe_result.items) >= 1
        assert len(orient_result.items) >= 1

    def test_goal_always_included(self):
        selector = ContextSelector(working_memory=None, tools=[])
        result = selector.select_context(
            phase="observe",
            goal="IMPORTANT_GOAL_MARKER",
            memory_context={},
            history=[],
            max_tokens=50,
        )
        goal_items = [item for item in result.items if item.source == "goal"]
        assert len(goal_items) >= 1
        assert "IMPORTANT_GOAL_MARKER" in goal_items[0].content

    def test_update_tool_list(self):
        selector = ContextSelector(tools=["old_tool"])
        assert selector._tools == ["old_tool"]
        selector.update_tool_list(["new_tool_a", "new_tool_b"])
        assert selector._tools == ["new_tool_a", "new_tool_b"]


class TestContextChunk:
    def test_chunk_defaults(self):
        chunk = ContextChunk(content="test content", source="goal")
        assert chunk.content == "test content"
        assert chunk.source == "goal"
        assert chunk.relevance_score == 0.0
        assert chunk.token_estimate == 0

    def test_chunk_with_scores(self):
        chunk = ContextChunk(
            content="important memory",
            source="working_memory",
            relevance_score=0.85,
            token_estimate=4,
            phase_relevance={"observe": 1.0, "orient": 0.5},
        )
        assert chunk.relevance_score == 0.85
        assert chunk.phase_relevance["observe"] == 1.0


class TestSelectedContext:
    def test_tool_list_fallback(self):
        ctx = SelectedContext(phase="act", items=[], total_tokens=0, token_budget=1000)
        assert ctx.get_tool_list("file_read, web_search") == "file_read, web_search"

    def test_tool_list_from_items(self):
        ctx = SelectedContext(
            phase="act",
            items=[
                ContextChunk(content="python_exec", source="tool_schema", token_estimate=2),
                ContextChunk(content="file_read", source="tool_schema", token_estimate=2),
            ],
            total_tokens=4,
            token_budget=1000,
        )
        tools = ctx.get_tool_list("default")
        assert "python_exec" in tools
        assert "file_read" in tools
