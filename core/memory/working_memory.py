from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """
    记忆项数据结构
    """

    id: str
    content: str
    item_type: str = "observation"  # observation, reflection, plan, action, result
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0-1.0 重要性评分
    decay_rate: float = 0.01  # 遗忘速率


class WorkingMemory:
    """
    工作记忆（短期记忆）
    用于存储当前会话的上下文信息，有固定容量限制
    """

    def __init__(self, max_size: int = 100, max_age_minutes: int = 60):
        """
        初始化工作记忆

        Args:
            max_size: 最大存储项数
            max_age_minutes: 最大保存时间（分钟）
        """
        self.memory_store: deque = deque(maxlen=max_size)
        self.max_size = max_size
        self.max_age_minutes = max_age_minutes
        self.item_counter: int = 0

    def add(self, content: str, item_type: str = "observation", importance: float = 0.5, metadata: Optional[Dict] = None) -> str:
        """
        添加记忆项

        Args:
            content: 记忆内容
            item_type: 类型
            importance: 重要性评分 (0-1)
            metadata: 附加元数据

        Returns:
            记忆项ID
        """
        self._cleanup_expired()

        item_id = f"wm_{self.item_counter}"
        self.item_counter += 1

        item = MemoryItem(
            id=item_id,
            content=content,
            item_type=item_type,
            importance=max(0.0, min(1.0, importance)),
            metadata=metadata or {},
        )

        self.memory_store.append(item)
        return item_id

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """
        根据ID获取记忆项

        Args:
            item_id: 记忆项ID

        Returns:
            记忆项或None
        """
        for item in self.memory_store:
            if item.id == item_id:
                return item
        return None

    def get_recent(self, count: int = 10, min_importance: float = 0.0) -> List[MemoryItem]:
        """
        获取最近的记忆项

        Args:
            count: 获取数量
            min_importance: 最小重要性过滤

        Returns:
            记忆项列表
        """
        filtered_items = [item for item in self.memory_store if item.importance >= min_importance]
        return filtered_items[-count:]

    def get_by_type(self, item_type: str, count: int = 20) -> List[MemoryItem]:
        """
        根据类型获取记忆项

        Args:
            item_type: 类型
            count: 最大数量

        Returns:
            记忆项列表
        """
        filtered_items = [item for item in self.memory_store if item.item_type == item_type]
        return filtered_items[-count:]

    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """
        搜索记忆项

        Args:
            query: 搜索关键词
            limit: 返回数量上限

        Returns:
            匹配的记忆项列表
        """
        results = []
        query_lower = query.lower()

        for item in self.memory_store:
            if query_lower in item.content.lower():
                results.append(item)
            elif "tags" in item.metadata and any(query_lower in tag.lower() for tag in item.metadata.get("tags", [])):
                results.append(item)

        return results[:limit]

    def remove(self, item_id: str) -> bool:
        """
        删除记忆项

        Args:
            item_id: 记忆项ID

        Returns:
            是否删除成功
        """
        for i, item in enumerate(self.memory_store):
            if item.id == item_id:
                del self.memory_store[i]
                return True
        return False

    def clear(self):
        """清空工作记忆"""
        self.memory_store.clear()

    def size(self) -> int:
        """获取当前存储的项数"""
        return len(self.memory_store)

    def _cleanup_expired(self):
        """清理过期的记忆项"""
        now = datetime.now()
        cutoff = timedelta(minutes=self.max_age_minutes)

        # 创建新的deque只保留未过期的
        valid_items = deque(maxlen=self.max_size)
        for item in self.memory_store:
            if now - item.timestamp < cutoff:
                valid_items.append(item)

        self.memory_store = valid_items

    def to_context_string(self, max_tokens: int = 4000) -> str:
        """
        格式化为上下文字符串

        Args:
            max_tokens: 最大token数限制

        Returns:
            格式化的上下文字符串
        """
        lines = []
        current_length = 0

        for item in reversed(self.memory_store):  # 从新到旧
            line = f"[{item.item_type.upper()} {item.timestamp.strftime('%H:%M:%S')}] {item.content}"
            line_length = len(line)

            if current_length + line_length > max_tokens:
                break

            lines.insert(0, line)
            current_length += line_length

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据字典
        """
        type_counts: Dict[str, int] = {}
        for item in self.memory_store:
            type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1

        return {
            "total_items": len(self.memory_store),
            "max_capacity": self.max_size,
            "type_distribution": type_counts,
            "average_importance": (
                sum(item.importance for item in self.memory_store) / len(self.memory_store)
                if self.memory_store
                else 0
            ),
        }
