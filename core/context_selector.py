"""Context Selector — dynamic context selection per OODA phase.

Maps to the Harness paper's "上下文选择" responsibility: dynamically
decide what information to inject into each LLM call, rather than
passing all available context.

Phase-specific strategies:
- Observe: recent observations, environment state
- Orient: relevant memories, similar past episodes
- Decide: plan tree, available tools, constraints
- Act: tool schemas, execution context
"""

import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    """A chunk of context with relevance scoring."""
    content: str
    source: str  # "working_memory" | "semantic_memory" | "tool_schema" | "plan" | "goal" | "history"
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    token_estimate: int = 0
    phase_relevance: Dict[str, float] = Field(default_factory=dict)


class SelectedContext(BaseModel):
    """Result of context selection for a single phase."""
    phase: str
    items: List[ContextChunk] = Field(default_factory=list)
    total_tokens: int = 0
    token_budget: int = 0
    overflow_items: int = 0
    decision_log: str = ""

    def to_context_dict(self) -> Dict[str, Any]:
        """Convert to a flat dict for prompt template rendering."""
        return {
            "selected_memories": [
                item.content for item in self.items
                if item.source in ("working_memory", "semantic_memory", "episodic_memory")
            ],
            "relevant_tools": [
                item.content for item in self.items if item.source == "tool_schema"
            ],
            "plan_summary": next(
                (item.content for item in self.items if item.source == "plan"), ""
            ),
            "goal": next(
                (item.content for item in self.items if item.source == "goal"), ""
            ),
            "relevant_history": [
                item.content for item in self.items if item.source == "history"
            ],
        }

    def get_tool_list(self, default_tools: str) -> str:
        """Get tool list from selected context or fall back to default."""
        tool_items = [item.content for item in self.items if item.source == "tool_schema"]
        return ", ".join(tool_items) if tool_items else default_tools


class ContextSelector:
    """Selects and budgets context for LLM calls per OODA phase.

    Different phases need different context:
    - Observe: what just happened (observations, tool results)
    - Orient: what does it mean (relevant memories, insights)
    - Decide: what can I do (plan, tools, constraints)
    - Act: how do I do it (tool schemas, execution context)
    """

    # ── Phase-specific source weights ────────────────────────────────────
    # Weight multiplier per (phase, source) pair

    PHASE_WEIGHTS: Dict[str, Dict[str, float]] = {
        "observe": {
            "working_memory": 1.0,
            "history": 0.9,
            "tool_schema": 0.3,
            "semantic_memory": 0.3,
            "plan": 0.5,
            "goal": 1.0,
        },
        "orient": {
            "working_memory": 0.5,
            "semantic_memory": 1.0,
            "plan": 0.6,
            "goal": 0.6,
            "history": 0.4,
            "tool_schema": 0.2,
        },
        "decide": {
            "plan": 1.0,
            "tool_schema": 0.9,
            "goal": 0.8,
            "working_memory": 0.4,
            "semantic_memory": 0.5,
            "history": 0.3,
        },
        "act": {
            "tool_schema": 1.0,
            "plan": 0.7,
            "working_memory": 0.6,
            "history": 0.5,
            "goal": 0.3,
            "semantic_memory": 0.2,
        },
    }

    # Default weights for unknown phases
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "working_memory": 0.5,
        "semantic_memory": 0.5,
        "tool_schema": 0.5,
        "plan": 0.5,
        "goal": 0.5,
        "history": 0.5,
    }

    def __init__(self, working_memory=None, semantic_memory=None, tools: List[str] | None = None,
                 embedding_enabled: bool = True):
        self._working_memory = working_memory
        self._semantic_memory = semantic_memory
        self._tools: List[str] = tools if tools is not None else []
        self._embedding_enabled = embedding_enabled

    def select_context(self, phase: str, goal: str, memory_context: Dict,
                       history: List[Dict], max_tokens: int) -> SelectedContext:
        """Select the best context chunks for a given phase within a token budget.

        Args:
            phase: OODA phase name ("observe", "orient", "decide", "act")
            goal: The current task goal
            memory_context: Dict with plan_content, tool_names, etc.
            history: List of previous step dicts with phase, action, observation
            max_tokens: Maximum tokens for the selected context

        Returns:
            SelectedContext with chosen items and budget info
        """
        candidates = self._gather_candidates(phase, goal, memory_context, history)
        # Apply phase weights to relevance
        weights = self.PHASE_WEIGHTS.get(phase, self.DEFAULT_WEIGHTS)
        for chunk in candidates:
            phase_weight = weights.get(chunk.source, 0.5)
            chunk.relevance_score = chunk.relevance_score * phase_weight

        return self._apply_token_budget(candidates, max_tokens, phase)

    # ── Candidate Gathering ──────────────────────────────────────────────

    def _gather_candidates(self, phase: str, goal: str, memory_context: Dict,
                           history: List[Dict]) -> List[ContextChunk]:
        """Collect all candidate context chunks with initial relevance scores."""
        candidates: List[ContextChunk] = []

        # 1. Goal chunk (always high relevance)
        candidates.append(ContextChunk(
            content=goal[:500],
            source="goal",
            relevance_score=1.0,
            token_estimate=self._estimate_tokens(goal),
        ))

        # 2. Plan chunk
        plan_content = memory_context.get("plan_content", "")
        if plan_content:
            relevance = self._keyword_match_score(plan_content, goal)
            candidates.append(ContextChunk(
                content=plan_content[:1000],
                source="plan",
                relevance_score=0.6 + 0.4 * relevance,
                token_estimate=self._estimate_tokens(plan_content[:1000]),
            ))

        # 3. Working memory chunks
        if self._working_memory:
            recent = self._working_memory.get_recent(10)
            for i, item in enumerate(recent):
                content = item.content if hasattr(item, 'content') else str(item)
                recency_score = 1.0 - (i / max(len(recent), 1))
                keyword_score = self._keyword_match_score(content, goal)
                relevance = recency_score * 0.3 + keyword_score * 0.4 + item.importance * 0.3 if hasattr(item, 'importance') else 0.5
                candidates.append(ContextChunk(
                    content=content[:500],
                    source="working_memory",
                    relevance_score=relevance,
                    token_estimate=self._estimate_tokens(content[:500]),
                ))

        # 4. History chunks
        for i, step in enumerate(history[-5:]):
            chunks = []
            if step.get("action"):
                chunks.append(f"Action: {step['action'][:300]}")
            if step.get("observation"):
                chunks.append(f"Observation: {step['observation'][:300]}")
            if chunks:
                content = " | ".join(chunks)
                recency = 1.0 - ((len(history[-5:]) - 1 - i) / max(len(history[-5:]), 1))
                candidates.append(ContextChunk(
                    content=content,
                    source="history",
                    relevance_score=0.3 + 0.5 * recency,
                    token_estimate=self._estimate_tokens(content),
                ))

        # 5. Tool schema chunks
        tool_names = memory_context.get("tool_names", self._tools)
        if tool_names:
            tool_list = ", ".join(tool_names[:20])
            candidates.append(ContextChunk(
                content=f"Available tools: {tool_list}",
                source="tool_schema",
                relevance_score=0.5,
                token_estimate=self._estimate_tokens(tool_list),
            ))

        # 6. Semantic memory chunks (if search available)
        if self._semantic_memory and hasattr(self._semantic_memory, 'semantic_search'):
            try:
                results = self._semantic_memory.semantic_search(goal, limit=3, min_confidence=0.3)
                for r in results:
                    content = r.content if hasattr(r, 'content') else str(r)
                    confidence = r.confidence if hasattr(r, 'confidence') else 0.5
                    candidates.append(ContextChunk(
                        content=content[:500],
                        source="semantic_memory",
                        relevance_score=confidence * 0.7,
                        token_estimate=self._estimate_tokens(content[:500]),
                    ))
            except Exception:
                pass  # Graceful degradation

        return candidates

    # ── Token Budgeting ──────────────────────────────────────────────────

    def _apply_token_budget(self, candidates: List[ContextChunk], max_tokens: int,
                            phase: str) -> SelectedContext:
        """Greedy selection: pick highest density chunks within budget."""
        # Sort by relevance_score / token_estimate (information density)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.relevance_score / max(c.token_estimate, 1),
            reverse=True,
        )

        selected: List[ContextChunk] = []
        total_tokens = 0
        overflow = 0

        for chunk in sorted_candidates:
            if total_tokens + chunk.token_estimate <= max_tokens:
                selected.append(chunk)
                total_tokens += chunk.token_estimate
            else:
                overflow += 1

        # Decision log
        sources = set(c.source for c in selected)
        log_parts = [
            f"Phase '{phase}': selected {len(selected)}/{len(candidates)} chunks "
            f"({total_tokens}/{max_tokens} tokens) from sources: {sources}"
        ]
        if overflow > 0:
            log_parts.append(f"({overflow} items overflowed)")

        return SelectedContext(
            phase=phase,
            items=selected,
            total_tokens=total_tokens,
            token_budget=max_tokens,
            overflow_items=overflow,
            decision_log=" ".join(log_parts),
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return max(1, len(text) // 4)

    @staticmethod
    def _keyword_match_score(text: str, query: str) -> float:
        """Simple keyword overlap score between text and query."""
        if not query or not text:
            return 0.0
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        text_words = set(re.findall(r'\b\w+\b', text.lower()))
        if not query_words:
            return 0.0
        overlap = query_words & text_words
        return len(overlap) / len(query_words)

    def update_tool_list(self, tools: List[str]) -> None:
        """Update the available tools list."""
        self._tools = tools
