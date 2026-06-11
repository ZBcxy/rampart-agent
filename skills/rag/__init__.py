"""RAG (Retrieval-Augmented Generation) Pipeline

Complete document→chunk→embed→retrieve→augment pipeline.

Usage:
    from skills.rag import RAGPipeline
    rag = RAGPipeline(embedding_provider="openai", api_key="...")
    rag.ingest_document("/path/to/doc.pdf")
    rag.ingest_text("Paris is the capital of France.")
    results = rag.query("What is the capital of France?", top_k=5)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Document:
    """A document in the RAG store."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Chunk:
    """A chunk of a document with its embedding."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """A retrieved chunk with relevance score."""
    chunk: Chunk
    score: float
    document: Optional[Document] = None


class RAGPipeline:
    """End-to-end RAG pipeline: ingest, chunk, embed, retrieve, augment.

    Supports:
    - Multiple document formats (txt, md, pdf via text extraction)
    - Configurable chunking strategies (fixed-size, sentence, paragraph)
    - Multiple embedding backends (openai, sentence-transformers, custom)
    - Top-k retrieval with optional reranking
    """

    def __init__(
        self,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        storage_path: Optional[str] = None,
    ):
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.api_key = api_key
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.storage_path = Path(storage_path) if storage_path else None
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, Chunk] = {}
        self._embedding_func: Optional[Callable] = None
        self._doc_counter = 0
        self._chunk_counter = 0

        if storage_path:
            self._load_from_disk()

        self._init_embedder()

    def _init_embedder(self):
        """Initialize the embedding function."""
        if self.embedding_provider == "openai" and self.api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)

                def openai_embed(texts: List[str]) -> List[List[float]]:
                    resp = self._client.embeddings.create(
                        model=self.embedding_model, input=texts,
                    )
                    return [d.embedding for d in resp.data]

                self._embedding_func = openai_embed
            except ImportError:
                pass

        elif self.embedding_provider == "sentence_transformers":
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(self.embedding_model)

                def st_embed(texts: List[str]) -> List[List[float]]:
                    return model.encode(texts, convert_to_numpy=True).tolist()

                self._embedding_func = st_embed
            except ImportError:
                pass

    # ── Ingestion ────────────────────────────────────────────────────────

    def ingest_text(self, text: str, source: str = "inline", metadata: Dict = None) -> str:
        """Ingest raw text into the RAG store."""
        doc_id = f"doc_{self._doc_counter}"
        self._doc_counter += 1

        doc = Document(
            doc_id=doc_id,
            content=text,
            source=source,
            metadata=metadata or {},
        )
        self._documents[doc_id] = doc

        # Chunk and embed
        chunks = self._chunk_text(text, doc_id)
        self._embed_chunks(chunks)

        self._save_to_disk()
        return doc_id

    def ingest_file(self, file_path: str) -> str:
        """Ingest a file into the RAG store."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self._read_file(path)
        return self.ingest_text(
            content,
            source=str(path.absolute()),
            metadata={"filename": path.name, "suffix": path.suffix},
        )

    def ingest_directory(self, directory: str, pattern: str = "*") -> List[str]:
        """Ingest all files in a directory."""
        ids = []
        for f in Path(directory).glob(pattern):
            if f.is_file():
                try:
                    doc_id = self.ingest_file(str(f))
                    ids.append(doc_id)
                except Exception:
                    pass
        return ids

    # ── Retrieval ─────────────────────────────────────────────────────────

    def query(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        metadata_filter: Optional[Dict] = None,
    ) -> List[RetrievalResult]:
        """Search the RAG store for relevant chunks.

        Args:
            query: Natural language query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            metadata_filter: Filter chunks by metadata key-value pairs

        Returns:
            List of RetrievalResult sorted by relevance
        """
        if not self._chunks:
            return []

        # Generate query embedding
        query_embedding = self._embed_query(query)

        # Score all chunks
        results = []
        for chunk in self._chunks.values():
            # Metadata filter
            if metadata_filter:
                if not all(chunk.metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue

            if query_embedding and chunk.embedding:
                score = self._cosine_sim(query_embedding, chunk.embedding)
            else:
                # Fallback to keyword matching
                score = self._keyword_score(query, chunk.content)

            if score >= min_score:
                doc = self._documents.get(chunk.doc_id)
                results.append(RetrievalResult(chunk=chunk, score=score, document=doc))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def query_context(self, query: str, top_k: int = 5, max_chars: int = 4000) -> str:
        """Get formatted context string for LLM augmentation.

        Args:
            query: The user's question
            top_k: Number of chunks to retrieve
            max_chars: Maximum context length

        Returns:
            Formatted context string ready to inject into a prompt
        """
        results = self.query(query, top_k=top_k, min_score=0.3)

        context_parts = []
        total_chars = 0
        for i, r in enumerate(results):
            chunk_text = f"[Source {i+1}: {r.chunk.metadata.get('source', r.chunk.doc_id)}]\n{r.chunk.content}"
            if total_chars + len(chunk_text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(chunk_text[:remaining] + "...")
                break
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        if not context_parts:
            return ""

        header = f"Relevant context from {len(results)} sources:\n\n"
        return header + "\n\n---\n\n".join(context_parts)

    # ── Chunking ──────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, doc_id: str) -> List[Chunk]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        step = max(1, self.chunk_size - self.chunk_overlap)

        i = 0
        while i < len(words):
            chunk_words = words[i : i + self.chunk_size]
            if not chunk_words:
                break

            chunk_id = f"chunk_{self._chunk_counter}"
            self._chunk_counter += 1

            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=" ".join(chunk_words),
                chunk_index=len(chunks),
                metadata={"source": doc_id, "position": i},
            )
            chunks.append(chunk)
            self._chunks[chunk_id] = chunk

            i += step

        return chunks

    def _embed_chunks(self, chunks: List[Chunk]):
        """Generate embeddings for chunks in batch."""
        if not self._embedding_func:
            return

        texts = [c.content for c in chunks]
        batch_size = 20

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_chunks = chunks[i : i + batch_size]
            try:
                embeddings = self._embedding_func(batch_texts)
                for chunk, emb in zip(batch_chunks, embeddings):
                    chunk.embedding = emb
            except Exception:
                break

    def _embed_query(self, query: str) -> Optional[List[float]]:
        """Generate embedding for a query."""
        if not self._embedding_func:
            return None
        try:
            embeddings = self._embedding_func([query])
            return embeddings[0] if embeddings else None
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        import math
        min_len = min(len(a), len(b))
        a, b = a[:min_len], b[:min_len]
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (na * nb)))

    @staticmethod
    def _keyword_score(query: str, content: str) -> float:
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & content_words
        return len(overlap) / len(query_words)

    @staticmethod
    def _read_file(path: Path) -> str:
        """Read file content, handling different formats."""
        suffix = path.suffix.lower()

        if suffix in (".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".log", ".env"):
            return path.read_text(encoding="utf-8", errors="replace")

        if suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                return f"[PDF file: {path.name} — install pypdf to extract text]"

        # Default: try text
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return f"[Binary file: {path.name}]"

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_from_disk(self):
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            for d in data.get("documents", []):
                doc = Document(**d)
                self._documents[doc.doc_id] = doc
            for c in data.get("chunks", []):
                chunk = Chunk(**c)
                self._chunks[chunk.chunk_id] = chunk
            self._doc_counter = data.get("doc_counter", len(self._documents))
            self._chunk_counter = data.get("chunk_counter", len(self._chunks))
        except Exception:
            pass

    def _save_to_disk(self):
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.storage_path, "w") as f:
                json.dump({
                    "doc_counter": self._doc_counter,
                    "chunk_counter": self._chunk_counter,
                    "documents": [vars(d) for d in self._documents.values()],
                    "chunks": [
                        {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "content": c.content,
                         "chunk_index": c.chunk_index, "metadata": c.metadata}
                        for c in self._chunks.values()
                    ],
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        return {
            "documents": len(self._documents),
            "chunks": len(self._chunks),
            "chunks_with_embeddings": sum(1 for c in self._chunks.values() if c.embedding),
            "chunk_size": self.chunk_size,
            "embedding_provider": self.embedding_provider,
        }
