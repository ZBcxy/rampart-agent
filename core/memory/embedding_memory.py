"""Embedding-based Semantic Memory

Extends SemanticMemory with real vector embeddings for semantic search.
Falls back gracefully to keyword matching when no embedding provider is available.
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .semantic_memory import MemoryVector, SemanticMemory


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    provider: str = "openai"  # openai, sentence_transformers, custom
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: Optional[str] = None
    batch_size: int = 20
    cache_embeddings: bool = True


class EmbeddingSemanticMemory(SemanticMemory):
    """Semantic memory with vector embedding support for true semantic search.

    Uses text embeddings (via OpenAI, sentence-transformers, or custom provider)
    to enable similarity-based retrieval.
    Falls back to keyword matching when embeddings are unavailable.

    Usage:
        memory = EmbeddingSemanticMemory(
            storage_path="~/.polaris/memory/semantic.json",
            embedding_config=EmbeddingConfig(provider="openai", api_key="...")
        )
        memory.add("The capital of France is Paris", tags=["geography"])
        results = memory.semantic_search("What is the capital of France?")
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        embedding_config: Optional[EmbeddingConfig] = None,
    ):
        """
        Initialize embeddable semantic memory.

        Args:
            storage_path: Path for persistent storage
            embedding_config: Configuration for embedding generation
        """
        super().__init__(storage_path)
        self.embedding_config = embedding_config or EmbeddingConfig()
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_func: Optional[Callable] = None
        self._embedding_available = False

        if embedding_config:
            self._initialize_embedding_provider()

    def _initialize_embedding_provider(self):
        """Try to initialize the embedding provider."""
        config = self.embedding_config

        if config.provider == "openai":
            try:
                import openai

                if config.api_key:
                    self._embedding_func = self._openai_embed
                    self._embedding_available = True
            except ImportError:
                pass

        elif config.provider == "sentence_transformers":
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(config.model)
                self._embedding_func = self._sentence_transformer_embed
                self._embedding_available = True
            except ImportError:
                pass

        elif config.provider == "custom" and config.api_key:
            # Custom embedding endpoint
            self._embedding_func = self._custom_api_embed
            self._embedding_available = True

    def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        import openai

        client = openai.OpenAI(api_key=self.embedding_config.api_key)
        response = client.embeddings.create(
            model=self.embedding_config.model,
            input=texts,
        )
        return [d.embedding for d in response.data]

    def _sentence_transformer_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers (local)."""
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def _custom_api_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using a custom API endpoint."""
        import requests

        response = requests.post(
            self.embedding_config.api_key,  # api_key used as endpoint URL in custom mode
            json={"texts": texts, "model": self.embedding_config.model},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def add(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        source: str = "internal",
        confidence: float = 0.8,
    ) -> str:
        """
        Add a memory item with automatic embedding generation.

        Args:
            content: Knowledge content
            metadata: Additional metadata
            tags: Tags for categorization
            source: Source of the knowledge
            confidence: Confidence in this knowledge

        Returns:
            Memory ID
        """
        # Generate embedding if available
        embedding = None
        if self._embedding_available and self._embedding_func:
            if self.embedding_config.cache_embeddings:
                cache_key = content[:200]
                if cache_key in self._embedding_cache:
                    embedding = self._embedding_cache[cache_key]
                else:
                    try:
                        embeddings = self._embedding_func([content])
                        embedding = embeddings[0] if embeddings else None
                        self._embedding_cache[cache_key] = embedding
                    except Exception:
                        pass
            else:
                try:
                    embeddings = self._embedding_func([content])
                    embedding = embeddings[0] if embeddings else None
                except Exception:
                    pass

        return super().add(
            content=content,
            metadata=metadata,
            tags=tags,
            source=source,
            confidence=confidence,
            embedding=embedding,
        )

    def add_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Add multiple memory items at once, generating embeddings in batch.

        Args:
            items: List of dicts with content, metadata, tags, source, confidence

        Returns:
            List of memory IDs
        """
        ids = []

        # Batch generate embeddings
        if self._embedding_available and self._embedding_func:
            texts = [item["content"] for item in items]
            try:
                batch_embeddings = self._embedding_func(texts)
            except Exception:
                batch_embeddings = [None] * len(items)
        else:
            batch_embeddings = [None] * len(items)

        for item, embedding in zip(items, batch_embeddings):
            mem_id = super().add(
                content=item["content"],
                metadata=item.get("metadata"),
                tags=item.get("tags"),
                source=item.get("source", "internal"),
                confidence=item.get("confidence", 0.8),
                embedding=embedding,
            )
            ids.append(mem_id)

        return ids

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        tags: Optional[List[str]] = None,
        use_embeddings: bool = True,
        hybrid_weight: float = 0.7,
    ) -> List[Tuple[MemoryVector, float]]:
        """
        Perform semantic search using embeddings.

        Combines embedding similarity with keyword matching (hybrid search).

        Args:
            query: Natural language query
            limit: Maximum results
            min_confidence: Minimum confidence filter
            tags: Optional tags filter
            use_embeddings: Whether to use embedding similarity
            hybrid_weight: Weight of embedding score vs keyword score (0-1)

        Returns:
            List of (MemoryVector, score) tuples, sorted by relevance
        """
        # Get keyword matches
        keyword_results = super().search(
            query=query,
            limit=max(limit * 3, 50),  # Get more candidates for reranking
            min_confidence=min_confidence,
            tags=tags,
        )
        keyword_scores = {mem.id: score for mem, score in keyword_results}

        if not use_embeddings or not self._embedding_available or not self._embedding_func:
            # Pure keyword search fallback
            return keyword_results[:limit]

        # Generate query embedding
        try:
            query_embeddings = self._embedding_func([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
        except Exception:
            return keyword_results[:limit]

        if not query_embedding:
            return keyword_results[:limit]

        # Score all memories with embeddings
        scored_results = []
        for memory in self.memories.values():
            if memory.confidence < min_confidence:
                continue

            # Tag filter
            if tags:
                mem_tags_lower = [t.lower() for t in memory.tags]
                if not any(t.lower() in mem_tags_lower for t in tags):
                    continue

            # Calculate scores
            embedding_score = 0.0
            if memory.embedding and query_embedding:
                embedding_score = self._cosine_similarity(query_embedding, memory.embedding)

            keyword_score = keyword_scores.get(memory.id, 0.0)

            # Hybrid score
            if memory.embedding:
                hybrid_score = hybrid_weight * embedding_score + (1 - hybrid_weight) * keyword_score
            else:
                hybrid_score = keyword_score

            if hybrid_score > 0:
                self._record_access(memory)
                scored_results.append((memory, hybrid_score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:limit]

    def find_similar(
        self,
        memory_id: str,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Tuple[MemoryVector, float]]:
        """
        Find memories similar to a given memory.

        Args:
            memory_id: ID of the reference memory
            limit: Maximum results
            threshold: Minimum similarity score

        Returns:
            List of (MemoryVector, score) tuples
        """
        reference = self.get(memory_id)
        if not reference or not reference.embedding:
            return []

        results = []
        for memory in self.memories.values():
            if memory.id == memory_id:
                continue
            if not memory.embedding:
                continue

            similarity = self._cosine_similarity(reference.embedding, memory.embedding)
            if similarity >= threshold:
                self._record_access(memory)
                results.append((memory, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def generate_missing_embeddings(self) -> int:
        """
        Generate embeddings for all memories that lack them.

        Returns:
            Number of embeddings generated
        """
        if not self._embedding_available or not self._embedding_func:
            return 0

        missing = [mem for mem in self.memories.values() if not mem.embedding]
        if not missing:
            return 0

        generated = 0
        batch_size = self.embedding_config.batch_size

        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            texts = [mem.content for mem in batch]

            try:
                embeddings = self._embedding_func(texts)
                for mem, emb in zip(batch, embeddings):
                    mem.embedding = emb
                    generated += 1
            except Exception:
                break

        if generated > 0:
            self._save_to_disk()

        return generated

    def clear_embedding_cache(self):
        """Clear the local embedding cache."""
        self._embedding_cache.clear()

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0 to 1)
        """
        if len(a) != len(b):
            # Pad or truncate to match
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        # Cosine sim is between -1 and 1, but for text embeddings it's typically 0-1
        return max(0.0, min(1.0, similarity))

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embedding coverage."""
        total = len(self.memories)
        with_embeddings = sum(1 for m in self.memories.values() if m.embedding)

        return {
            "total_memories": total,
            "with_embeddings": with_embeddings,
            "coverage_rate": with_embeddings / max(total, 1),
            "provider": self.embedding_config.provider,
            "model": self.embedding_config.model,
            "cached_embeddings": len(self._embedding_cache),
        }
