import pytest
from core.memory import WorkingMemory, EpisodicMemory, SemanticMemory


class TestWorkingMemory:
    """Tests for WorkingMemory"""

    def test_add_and_get_memory(self):
        """Test adding and retrieving memory items"""
        wm = WorkingMemory()
        item_id = wm.add(
            content="Test memory item",
            item_type="observation",
            importance=0.8,
        )
        assert item_id is not None

        item = wm.get(item_id)
        assert item is not None
        assert item.content == "Test memory item"
        assert item.item_type == "observation"
        assert item.importance == 0.8

    def test_get_recent_memories(self):
        """Test getting recent memories"""
        wm = WorkingMemory()
        for i in range(15):
            wm.add(content=f"Memory {i}", importance=0.5 + i/30)

        recent = wm.get_recent(10)
        assert len(recent) == 10
        assert recent[-1].content == "Memory 14"

    def test_get_by_type(self):
        """Test getting memories by type"""
        wm = WorkingMemory()
        wm.add(content="Observation 1", item_type="observation")
        wm.add(content="Action 1", item_type="action")
        wm.add(content="Observation 2", item_type="observation")

        observations = wm.get_by_type("observation")
        assert len(observations) == 2

    def test_search_memories(self):
        """Test searching memories"""
        wm = WorkingMemory()
        wm.add(content="This is about cats", importance=0.8)
        wm.add(content="This is about dogs", importance=0.8)

        results = wm.search("cats")
        assert len(results) == 1
        assert "cats" in results[0].content

    def test_memory_expiration(self):
        """Test that old memories expire"""
        wm = WorkingMemory(max_age_minutes=0.001)
        wm.add(content="Temporary memory")
        # Manually trigger cleanup
        wm._cleanup_expired()

    def test_remove_memory(self):
        """Test removing memories"""
        wm = WorkingMemory()
        item_id = wm.add(content="To be removed")
        assert wm.get(item_id) is not None

        success = wm.remove(item_id)
        assert success
        assert wm.get(item_id) is None

    def test_clear_memory(self):
        """Test clearing all memories"""
        wm = WorkingMemory()
        for i in range(5):
            wm.add(content=f"Memory {i}")

        assert wm.size() == 5
        wm.clear()
        assert wm.size() == 0

    def test_get_statistics(self):
        """Test getting memory statistics"""
        wm = WorkingMemory()
        wm.add(content="Mem 1", item_type="observation", importance=0.5)
        wm.add(content="Mem 2", item_type="action", importance=0.8)

        stats = wm.get_statistics()
        assert stats["total_items"] == 2
        assert "type_distribution" in stats


class TestEpisodicMemory:
    """Tests for EpisodicMemory"""

    def test_add_and_get_episode(self):
        """Test adding and retrieving episodes"""
        em = EpisodicMemory()
        ep_id = em.add(
            user_input="What's the weather?",
            agent_response="It's sunny!",
            success=True,
            execution_time=0.5,
            importance=0.7,
            tags=["weather"],
        )
        assert ep_id is not None

        episode = em.get(ep_id)
        assert episode is not None
        assert episode.user_input == "What's the weather?"
        assert episode.agent_response == "It's sunny!"

    def test_get_recent_episodes(self):
        """Test getting recent episodes"""
        em = EpisodicMemory()
        for i in range(10):
            em.add(
                user_input=f"Question {i}",
                agent_response=f"Answer {i}",
                success=True,
            )

        recent = em.get_recent(5)
        assert len(recent) == 5
        assert recent[0].user_input == "Question 9"

    def test_search_episodes(self):
        """Test searching episodes"""
        em = EpisodicMemory()
        em.add(
            user_input="How to bake bread?",
            agent_response="Bread recipe...",
            success=True,
            tags=["cooking", "food"],
        )
        em.add(
            user_input="How to code Python?",
            agent_response="Python tutorial...",
            success=True,
            tags=["programming", "python"],
        )

        results = em.search("bread")
        assert len(results) >= 1

    def test_get_by_tag(self):
        """Test getting episodes by tag"""
        em = EpisodicMemory()
        em.add(
            user_input="Question 1",
            agent_response="Answer 1",
            success=True,
            tags=["important"],
        )
        em.add(
            user_input="Question 2",
            agent_response="Answer 2",
            success=True,
            tags=["important"],
        )

        important = em.get_by_tag("important")
        assert len(important) == 2

    def test_get_failed_episodes(self):
        """Test getting failed episodes"""
        em = EpisodicMemory()
        em.add(
            user_input="Success case",
            agent_response="Success!",
            success=True,
        )
        em.add(
            user_input="Failed case",
            agent_response="Error!",
            success=False,
        )

        failed = em.get_failed_episodes()
        assert len(failed) == 1

    def test_get_statistics(self):
        """Test getting episodic memory statistics"""
        em = EpisodicMemory()
        em.add("Input 1", "Output 1", True, execution_time=0.1)
        em.add("Input 2", "Output 2", False, execution_time=0.2)

        stats = em.get_statistics()
        assert stats["total_episodes"] == 2
        assert stats["success_rate"] == 0.5
        assert abs(stats["average_execution_time"] - 0.15) < 0.001


class TestSemanticMemory:
    """Tests for SemanticMemory"""

    def test_add_and_get_memory(self):
        """Test adding and retrieving semantic memories"""
        sm = SemanticMemory()
        mem_id = sm.add(
            content="Python is a programming language",
            tags=["python", "programming"],
            source="internal",
            confidence=0.9,
        )
        assert mem_id is not None

        memory = sm.get(mem_id)
        assert memory is not None
        assert "Python" in memory.content

    def test_search_semantic_memory(self):
        """Test searching semantic memory"""
        sm = SemanticMemory()
        sm.add("Dogs are mammals", tags=["animals"])
        sm.add("Cats are mammals", tags=["animals"])
        sm.add("Birds can fly", tags=["animals", "birds"])

        results = sm.search("mammals", min_confidence=0.1)
        assert len(results) >= 2

        tagged = sm.search("animals", tags=["animals"])
        assert len(tagged) >= 3

    def test_get_all_tags(self):
        """Test getting all tags"""
        sm = SemanticMemory()
        sm.add("Content 1", tags=["tag1", "tag2"])
        sm.add("Content 2", tags=["tag2", "tag3"])

        all_tags = sm.get_all_tags()
        assert len(all_tags) == 3
        assert "tag1" in all_tags
        assert "tag2" in all_tags
        assert "tag3" in all_tags

    def test_update_memory(self):
        """Test updating memory"""
        sm = SemanticMemory()
        mem_id = sm.add("Old content", tags=["old"])

        success = sm.update(mem_id, content="New content", tags=["new"])
        assert success

        updated = sm.get(mem_id)
        assert updated.content == "New content"
        assert "new" in updated.tags

    def test_remove_memory(self):
        """Test removing memory"""
        sm = SemanticMemory()
        mem_id = sm.add("Content to remove")

        success = sm.remove(mem_id)
        assert success
        assert sm.get(mem_id) is None

    def test_get_statistics(self):
        """Test getting semantic memory statistics"""
        sm = SemanticMemory()
        sm.add("Mem 1", source="user", confidence=0.8)
        sm.add("Mem 2", source="system", confidence=0.9)

        stats = sm.get_statistics()
        assert stats["total_memories"] == 2
        assert "source_distribution" in stats
