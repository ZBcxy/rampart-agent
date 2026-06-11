"""Tests for the embedding-based semantic memory."""

import pytest
from core.memory.embedding_memory import EmbeddingConfig, EmbeddingSemanticMemory


class TestEmbeddingSemanticMemory:
    @pytest.fixture
    def memory(self):
        """Create a memory without any embedding provider (keyword-only mode)."""
        return EmbeddingSemanticMemory()

    def test_add_and_retrieve(self, memory):
        mem_id = memory.add("The capital of France is Paris", tags=["geography", "europe"])
        assert mem_id is not None
        assert memory.size() == 1

        result = memory.get(mem_id)
        assert result is not None
        assert "Paris" in result.content

    def test_semantic_search_fallback(self, memory):
        """Test that semantic_search falls back to keyword search when no embedding provider."""
        memory.add("Python is a programming language", tags=["technology"])
        memory.add("JavaScript is used for web development", tags=["technology"])
        memory.add("The Eiffel Tower is in Paris", tags=["landmarks"])

        results = memory.semantic_search("programming language", limit=5)
        assert len(results) > 0
        # Should find the Python entry
        contents = [r[0].content for r in results]
        assert any("Python" in c for c in contents)

    def test_semantic_search_with_tags(self, memory):
        memory.add("Python programming guide", tags=["tech", "python"])
        memory.add("Paris travel guide", tags=["travel", "france"])
        memory.add("Python for data science", tags=["tech", "python"])

        results = memory.semantic_search("Python", tags=["tech"], limit=5)
        assert len(results) > 0
        for mem, _ in results:
            assert "tech" in mem.tags

    def test_cosine_similarity(self, memory):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert memory._cosine_similarity(a, b) == pytest.approx(1.0, abs=0.001)

        c = [-1.0, -2.0, -3.0]
        assert memory._cosine_similarity(a, c) == pytest.approx(0.0, abs=0.001)

    def test_find_similar(self, memory):
        id1 = memory.add("Machine learning basics", tags=["ai"])
        memory.add("Deep learning advanced", tags=["ai"])
        memory.add("Cooking recipes", tags=["food"])

        # Without embeddings, find_similar returns empty
        results = memory.find_similar(id1)
        assert isinstance(results, list)

    def test_batch_add(self, memory):
        items = [
            {"content": "Fact one", "tags": ["test"]},
            {"content": "Fact two", "tags": ["test"]},
            {"content": "Fact three", "tags": ["test"]},
        ]
        ids = memory.add_batch(items)
        assert len(ids) == 3
        assert memory.size() == 3

    def test_statistics(self, memory):
        memory.add("Test content", tags=["test"])
        stats = memory.get_statistics()
        assert stats["total_memories"] == 1

    def test_embedding_stats(self, memory):
        memory.add("Test content")
        stats = memory.get_embedding_stats()
        assert stats["total_memories"] == 1
        assert stats["coverage_rate"] == 0.0  # No embeddings without provider

    def test_min_confidence_filter(self, memory):
        memory.add("Highly confident fact", confidence=0.9, tags=["reliable"])
        memory.add("Low confidence rumor", confidence=0.2, tags=["unreliable"])

        results = memory.semantic_search("fact", min_confidence=0.5)
        assert len(results) > 0
        for mem, _ in results:
            assert mem.confidence >= 0.5
