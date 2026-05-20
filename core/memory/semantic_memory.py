import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class MemoryVector:
    """
    语义记忆项
    存储知识片段及其元数据
    """

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # 向量表示（可选）
    tags: List[str] = field(default_factory=list)
    source: str = "internal"  # source of the memory
    confidence: float = 0.8
    access_count: int = 0
    last_access: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class SemanticMemory:
    """
    语义记忆（知识库）
    存储结构化的知识，支持语义搜索
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化语义记忆

        Args:
            storage_path: 持久化存储路径
        """
        self.memories: Dict[str, MemoryVector] = {}
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self.storage_path = Path(storage_path) if storage_path else None
        self.memory_counter = 0

        if self.storage_path:
            self._load_from_disk()

    def add(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        source: str = "internal",
        confidence: float = 0.8,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        添加语义记忆

        Args:
            content: 知识内容
            metadata: 附加元数据
            tags: 标签列表
            source: 来源
            confidence: 置信度
            embedding: 向量表示

        Returns:
            记忆ID
        """
        memory_id = f"sm_{self.memory_counter}"
        self.memory_counter += 1

        memory = MemoryVector(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            source=source,
            confidence=max(0.0, min(1.0, confidence)),
            embedding=embedding,
        )

        self.memories[memory_id] = memory

        # 更新索引
        for tag in memory.tags:
            self.tag_index[tag.lower()].add(memory_id)

        # 关键词索引
        keywords = self._extract_keywords(content)
        for keyword in keywords:
            self.keyword_index[keyword].add(memory_id)

        self._save_to_disk()

        return memory_id

    def get(self, memory_id: str) -> Optional[MemoryVector]:
        """
        根据ID获取记忆

        Args:
            memory_id: 记忆ID

        Returns:
            记忆项或None
        """
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            self._record_access(memory)
            return memory
        return None

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> List[Tuple[MemoryVector, float]]:
        """
        搜索语义记忆

        Args:
            query: 搜索查询
            limit: 返回数量限制
            min_confidence: 最小置信度
            tags: 标签过滤

        Returns:
            (记忆项, 评分) 列表
        """
        results: List[Tuple[MemoryVector, float]] = []

        # 基础关键词匹配
        query_lower = query.lower()
        query_keywords = self._extract_keywords(query)

        # 按标签过滤的候选集
        candidate_ids = set(self.memories.keys())
        if tags:
            tag_candidates = set()
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower in self.tag_index:
                    tag_candidates.update(self.tag_index[tag_lower])
            if tag_candidates:
                candidate_ids.intersection_update(tag_candidates)

        # 评分和排序
        for mem_id in candidate_ids:
            memory = self.memories[mem_id]

            if memory.confidence < min_confidence:
                continue

            score = self._calculate_match_score(query_lower, query_keywords, memory)

            if score > 0:
                results.append((memory, score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 记录访问并返回
        final_results = []
        for memory, score in results[:limit]:
            self._record_access(memory)
            final_results.append((memory, score))

        return final_results

    def get_by_tag(self, tag: str, limit: int = 50) -> List[MemoryVector]:
        """
        根据标签获取记忆

        Args:
            tag: 标签
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        tag_lower = tag.lower()
        if tag_lower not in self.tag_index:
            return []

        results = []
        for mem_id in list(self.tag_index[tag_lower])[:limit]:
            if mem_id in self.memories:
                memory = self.memories[mem_id]
                self._record_access(memory)
                results.append(memory)

        # 按最近访问排序
        results.sort(key=lambda x: x.last_access or x.created_at, reverse=True)
        return results

    def get_by_source(self, source: str, limit: int = 50) -> List[MemoryVector]:
        """
        根据来源获取记忆

        Args:
            source: 来源
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        results = [
            memory for memory in self.memories.values() if memory.source == source
        ]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        confidence: Optional[float] = None,
    ) -> bool:
        """
        更新记忆

        Args:
            memory_id: 记忆ID
            content: 新内容
            metadata: 新元数据
            tags: 新标签
            confidence: 新置信度

        Returns:
            是否更新成功
        """
        if memory_id not in self.memories:
            return False

        memory = self.memories[memory_id]

        if content is not None:
            # 需要重建关键词索引
            old_keywords = self._extract_keywords(memory.content)
            memory.content = content
            new_keywords = self._extract_keywords(content)

            # 移除旧关键词索引
            for keyword in old_keywords:
                if keyword in self.keyword_index and memory_id in self.keyword_index[keyword]:
                    self.keyword_index[keyword].remove(memory_id)

            # 添加新关键词索引
            for keyword in new_keywords:
                self.keyword_index[keyword].add(memory_id)

        if metadata is not None:
            memory.metadata = metadata

        if tags is not None:
            # 重建标签索引
            for old_tag in memory.tags:
                old_tag_lower = old_tag.lower()
                if old_tag_lower in self.tag_index and memory_id in self.tag_index[old_tag_lower]:
                    self.tag_index[old_tag_lower].remove(memory_id)

            memory.tags = tags
            for tag in tags:
                self.tag_index[tag.lower()].add(memory_id)

        if confidence is not None:
            memory.confidence = max(0.0, min(1.0, confidence))

        self._save_to_disk()
        return True

    def remove(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        if memory_id not in self.memories:
            return False

        memory = self.memories[memory_id]

        # 清理索引
        for tag in memory.tags:
            tag_lower = tag.lower()
            if tag_lower in self.tag_index and memory_id in self.tag_index[tag_lower]:
                self.tag_index[tag_lower].remove(memory_id)

        keywords = self._extract_keywords(memory.content)
        for keyword in keywords:
            if keyword in self.keyword_index and memory_id in self.keyword_index[keyword]:
                self.keyword_index[keyword].remove(memory_id)

        del self.memories[memory_id]
        self._save_to_disk()

        return True

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        return list(self.tag_index.keys())

    def size(self) -> int:
        """获取记忆数量"""
        return len(self.memories)

    def clear(self):
        """清空所有记忆"""
        self.memories.clear()
        self.tag_index.clear()
        self.keyword_index.clear()
        self._save_to_disk()

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        # 简单的关键词提取：去停用词、转小写、取较长的词
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        words = re.findall(r"\w+", text.lower())
        keywords = [word for word in words if word not in stopwords and len(word) >= 2]
        return keywords[:20]

    def _calculate_match_score(self, query_lower: str, query_keywords: List[str], memory: MemoryVector) -> float:
        """
        计算匹配分数

        Args:
            query_lower: 小写查询
            query_keywords: 查询关键词
            memory: 记忆项

        Returns:
            匹配分数 (0-1)
        """
        score = 0.0

        # 内容完全匹配
        if query_lower in memory.content.lower():
            score += 0.5

        # 关键词匹配
        content_lower = memory.content.lower()
        matched_keywords = [kw for kw in query_keywords if kw in content_lower]
        if matched_keywords:
            keyword_score = len(matched_keywords) / max(len(query_keywords), 1)
            score += keyword_score * 0.3

        # 标签匹配
        for tag in memory.tags:
            if tag.lower() in query_lower:
                score += 0.1

        # 置信度和访问频率加分
        score += memory.confidence * 0.1
        score += min(memory.access_count / 10, 0.1)

        return min(score, 1.0)

    def _record_access(self, memory: MemoryVector):
        """记录访问"""
        memory.access_count += 1
        memory.last_access = datetime.now()

    def _load_from_disk(self):
        """从磁盘加载"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for mem_data in data.get("memories", []):
                memory = MemoryVector(
                    id=mem_data["id"],
                    content=mem_data["content"],
                    metadata=mem_data.get("metadata", {}),
                    tags=mem_data.get("tags", []),
                    source=mem_data.get("source", "internal"),
                    confidence=mem_data.get("confidence", 0.8),
                    embedding=mem_data.get("embedding"),
                    access_count=mem_data.get("access_count", 0),
                    created_at=datetime.fromisoformat(mem_data["created_at"]),
                )

                if "last_access" in mem_data and mem_data["last_access"]:
                    memory.last_access = datetime.fromisoformat(mem_data["last_access"])

                self.memories[memory.id] = memory

                # 重建索引
                for tag in memory.tags:
                    self.tag_index[tag.lower()].add(memory.id)

                keywords = self._extract_keywords(memory.content)
                for keyword in keywords:
                    self.keyword_index[keyword].add(memory.id)

            self.memory_counter = data.get("memory_counter", len(self.memories))

        except Exception:
            pass

    def _save_to_disk(self):
        """保存到磁盘"""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "memory_counter": self.memory_counter,
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "metadata": m.metadata,
                    "tags": m.tags,
                    "source": m.source,
                    "confidence": m.confidence,
                    "embedding": m.embedding,
                    "access_count": m.access_count,
                    "created_at": m.created_at.isoformat(),
                    "last_access": m.last_access.isoformat() if m.last_access else None,
                }
                for m in self.memories.values()
            ],
        }

        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据字典
        """
        total = len(self.memories)
        if total == 0:
            return {"total_memories": 0}

        source_counts: Dict[str, int] = defaultdict(int)
        for m in self.memories.values():
            source_counts[m.source] += 1

        return {
            "total_memories": total,
            "unique_tags": len(self.tag_index),
            "source_distribution": dict(source_counts),
            "average_confidence": sum(m.confidence for m in self.memories.values()) / total,
            "total_accesses": sum(m.access_count for m in self.memories.values()),
        }
