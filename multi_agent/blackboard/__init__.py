"""Blackboard pattern implementation for multi-agent knowledge sharing.

The blackboard is a shared data structure that multiple specialized agents
can read from and write to. It serves as the central communication hub
for collaborative problem-solving.
"""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class EntryStatus(Enum):
    """Status of a blackboard entry."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    OBSOLETE = "obsolete"


@dataclass
class BlackboardEntry:
    """A single entry on the blackboard."""

    entry_id: str
    key: str
    value: Any
    author: str
    status: EntryStatus = EntryStatus.PROPOSED
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Blackboard:
    """Central blackboard for multi-agent collaboration.

    Provides a shared workspace where specialized agents can publish findings,
    read each other's contributions, and build on shared knowledge.

    Features:
    - Namespaced entries (by key prefix)
    - Subscription/notification system
    - Version tracking for entries
    - Confidence-weighted knowledge
    - Dependency tracking between entries
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._entries: Dict[str, BlackboardEntry] = {}
        self._key_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._author_index: Dict[str, Set[str]] = defaultdict(set)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self._entry_counter = 0
        self._max_entries = 10000

    def write(
        self,
        key: str,
        value: Any,
        author: str,
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Write an entry to the blackboard."""
        with self._lock:
            self._cleanup_if_needed()
            entry_id = f"bb_{self._entry_counter}"
            self._entry_counter += 1

            entry = BlackboardEntry(
                entry_id=entry_id,
                key=key,
                value=value,
                author=author,
                confidence=max(0.0, min(1.0, confidence)),
                tags=tags or [],
                dependencies=dependencies or [],
                metadata=metadata or {},
            )

            self._entries[entry_id] = entry
            self._key_index[key].append(entry_id)

            for tag in entry.tags:
                self._tag_index[tag.lower()].add(entry_id)

            self._author_index[author].add(entry_id)
            self._notify_subscribers(key, entry)

            return entry_id

    def read(self, entry_id: str) -> Optional[BlackboardEntry]:
        """Read a specific entry by ID."""
        with self._lock:
            return self._entries.get(entry_id)

    def read_by_key(self, key: str, limit: int = 50) -> List[BlackboardEntry]:
        """Read all entries for a given key, most recent first."""
        with self._lock:
            entry_ids = self._key_index.get(key, [])[-limit:]
            return [self._entries[eid] for eid in entry_ids if eid in self._entries][::-1]

    def query(
        self,
        key_prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        min_confidence: float = 0.0,
        status: Optional[EntryStatus] = None,
        limit: int = 100,
    ) -> List[BlackboardEntry]:
        """Query entries with flexible filtering."""
        candidates = set(self._entries.keys())

        if key_prefix:
            prefixed = set()
            for key, ids in self._key_index.items():
                if key.startswith(key_prefix):
                    prefixed.update(ids)
            candidates &= prefixed

        if tags:
            tag_set: Set[str] = set()
            for tag in tags:
                tag_set.update(self._tag_index.get(tag.lower(), set()))
            if not tag_set and tags:
                return []
            candidates &= tag_set

        if author:
            candidates &= self._author_index.get(author, set())

        results = []
        for eid in candidates:
            entry = self._entries.get(eid)
            if not entry:
                continue
            if entry.confidence < min_confidence:
                continue
            if status and entry.status != status:
                continue
            results.append(entry)

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def update(
        self,
        entry_id: str,
        value: Optional[Any] = None,
        confidence: Optional[float] = None,
        status: Optional[EntryStatus] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing entry."""
        with self._lock:
            if entry_id not in self._entries:
                return False
            entry = self._entries[entry_id]

            if value is not None:
                entry.value = value
            if confidence is not None:
                entry.confidence = max(0.0, min(1.0, confidence))
            if status is not None:
                entry.status = status
            if tags is not None:
                for old_tag in entry.tags:
                    self._tag_index[old_tag.lower()].discard(entry_id)
                entry.tags = tags
                for tag in tags:
                    self._tag_index[tag.lower()].add(entry_id)
            if metadata is not None:
                entry.metadata.update(metadata)

            entry.updated_at = datetime.now()
            entry.version += 1
            return True

    def subscribe(self, key_pattern: str, callback: Callable[[BlackboardEntry], None]):
        """Subscribe to changes on keys matching a pattern."""
        with self._lock:
            self._subscribers[key_pattern].append(callback)

    def unsubscribe(self, key_pattern: str, callback: Callable):
        """Remove a subscription."""
        with self._lock:
            if key_pattern in self._subscribers:
                try:
                    self._subscribers[key_pattern].remove(callback)
                except ValueError:
                    pass

    def _notify_subscribers(self, key: str, entry: BlackboardEntry):
        """Notify subscribers matching the key."""
        for pattern, callbacks in self._subscribers.items():
            if key.startswith(pattern) or key == pattern:
                for callback in callbacks:
                    try:
                        callback(entry)
                    except Exception:
                        pass

    def _cleanup_if_needed(self):
        """Remove oldest low-confidence entries if over capacity."""
        if len(self._entries) <= self._max_entries:
            return
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: (e.confidence, e.timestamp.timestamp()),
        )
        to_remove = sorted_entries[: len(self._entries) - self._max_entries + 100]
        for entry in to_remove:
            self._remove_entry_internal(entry.entry_id)

    def _remove_entry_internal(self, entry_id: str):
        """Internal remove without lock (caller must hold lock)."""
        entry = self._entries.pop(entry_id, None)
        if not entry:
            return
        if entry.key in self._key_index:
            self._key_index[entry.key] = [eid for eid in self._key_index[entry.key] if eid != entry_id]
            if not self._key_index[entry.key]:
                del self._key_index[entry.key]
        for tag in entry.tags:
            self._tag_index[tag.lower()].discard(entry_id)
        self._author_index[entry.author].discard(entry_id)

    def remove(self, entry_id: str) -> bool:
        """Remove an entry from the blackboard."""
        with self._lock:
            if entry_id not in self._entries:
                return False
            self._remove_entry_internal(entry_id)
            return True

    def clear(self):
        """Clear all entries from the blackboard."""
        with self._lock:
            self._entries.clear()
            self._key_index.clear()
            self._tag_index.clear()
            self._author_index.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get blackboard statistics."""
        with self._lock:
            status_counts: Dict[str, int] = defaultdict(int)
            for entry in self._entries.values():
                status_counts[entry.status.value] += 1

            return {
                "name": self.name,
                "total_entries": len(self._entries),
                "unique_keys": len(self._key_index),
                "unique_tags": len(self._tag_index),
                "unique_authors": len(self._author_index),
                "status_distribution": dict(status_counts),
                "average_confidence": (
                    sum(e.confidence for e in self._entries.values()) / len(self._entries)
                    if self._entries
                    else 0
                ),
            }

    def snapshot(self) -> Dict[str, Any]:
        """Create a JSON-serializable snapshot of the blackboard."""
        with self._lock:
            return {
                "name": self.name,
                "timestamp": datetime.now().isoformat(),
                "entries": [
                    {
                        "entry_id": e.entry_id,
                        "key": e.key,
                        "value": e.value,
                        "author": e.author,
                        "status": e.status.value,
                        "confidence": e.confidence,
                        "tags": e.tags,
                        "timestamp": e.timestamp.isoformat(),
                        "version": e.version,
                        "dependencies": e.dependencies,
                        "metadata": e.metadata,
                    }
                    for e in self._entries.values()
                ],
            }
