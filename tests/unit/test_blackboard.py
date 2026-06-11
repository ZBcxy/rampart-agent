"""Tests for the multi-agent blackboard."""

import pytest
from multi_agent.blackboard import Blackboard, BlackboardEntry, EntryStatus


class TestBlackboard:
    @pytest.fixture
    def bb(self):
        return Blackboard(name="test")

    def test_write_and_read(self, bb):
        entry_id = bb.write("test/key", "hello world", author="agent1")
        assert entry_id.startswith("bb_")

        entry = bb.read(entry_id)
        assert entry is not None
        assert entry.value == "hello world"
        assert entry.author == "agent1"

    def test_read_by_key(self, bb):
        bb.write("results/analysis", "finding 1", author="analyst")
        bb.write("results/analysis", "finding 2", author="analyst")
        bb.write("other/data", "irrelevant", author="other")

        results = bb.read_by_key("results/analysis")
        assert len(results) == 2

    def test_query_by_prefix(self, bb):
        bb.write("task/1/result", "result for task 1", author="agent1")
        bb.write("task/2/result", "result for task 2", author="agent2")
        bb.write("other/data", "something else", author="agent3")

        results = bb.query(key_prefix="task/")
        assert len(results) == 2

    def test_query_by_tag(self, bb):
        bb.write("data/1", "value1", author="agent1", tags=["important", "verified"])
        bb.write("data/2", "value2", author="agent2", tags=["draft"])
        bb.write("data/3", "value3", author="agent3", tags=["important"])

        results = bb.query(tags=["important"])
        assert len(results) == 2

    def test_query_by_author(self, bb):
        bb.write("data/1", "value1", author="agent_a")
        bb.write("data/2", "value2", author="agent_b")

        results = bb.query(author="agent_a")
        assert len(results) == 1

    def test_update_entry(self, bb):
        entry_id = bb.write("data/x", "original", author="agent1")
        assert bb.read(entry_id).value == "original"

        updated = bb.update(entry_id, value="updated", confidence=0.9)
        assert updated is True

        entry = bb.read(entry_id)
        assert entry.value == "updated"
        assert entry.confidence == 0.9
        assert entry.version == 2

    def test_remove_entry(self, bb):
        entry_id = bb.write("data/x", "to be removed", author="agent1")
        assert bb.read(entry_id) is not None

        removed = bb.remove(entry_id)
        assert removed is True
        assert bb.read(entry_id) is None

    def test_subscribe_notifications(self, bb):
        notifications = []

        def callback(entry):
            notifications.append(entry)

        bb.subscribe("alerts/", callback)
        bb.write("alerts/critical", "System down", author="monitor")

        assert len(notifications) == 1
        assert notifications[0].value == "System down"

    def test_statistics(self, bb):
        bb.write("data/1", "v1", author="agent1", tags=["tag1"])
        bb.write("data/2", "v2", author="agent2", tags=["tag2"])

        stats = bb.get_statistics()
        assert stats["total_entries"] == 2
        assert stats["unique_authors"] == 2
        assert stats["unique_tags"] == 2

    def test_snapshot(self, bb):
        bb.write("data/1", "value1", author="agent1")
        bb.write("data/2", "value2", author="agent2")

        snap = bb.snapshot()
        assert snap["name"] == "test"
        assert len(snap["entries"]) == 2

    def test_clear(self, bb):
        bb.write("data/1", "v1", author="agent1")
        assert bb.get_statistics()["total_entries"] == 1

        bb.clear()
        assert bb.get_statistics()["total_entries"] == 0
