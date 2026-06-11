import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional



@dataclass
class Episode:
    """
    情节记忆项
    记录完整的交互过程
    """

    id: str
    user_input: str
    agent_response: str
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    execution_time: float = 0.0
    plan_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5


class EpisodicMemory:
    """
    情节记忆（长期记忆）
    记录完整的交互历史，支持持久化存储
    """

    def __init__(self, storage_path: Optional[str] = None, max_episodes: int = 1000):
        """
        初始化情节记忆

        Args:
            storage_path: 持久化存储路径
            max_episodes: 最大存储的情节数
        """
        self.episodes: Dict[str, Episode] = {}
        self.max_episodes = max_episodes
        self.storage_path = Path(storage_path) if storage_path else None
        self.episode_counter = 0

        if self.storage_path:
            self._load_from_disk()

    def add(
        self,
        user_input: str,
        agent_response: str,
        success: bool = True,
        execution_time: float = 0.0,
        plan_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> str:
        """
        添加新的情节记忆

        Args:
            user_input: 用户输入
            agent_response: 智能体响应
            success: 是否成功
            execution_time: 执行时间
            plan_id: 计划ID
            metadata: 附加元数据
            tags: 标签列表
            importance: 重要性评分

        Returns:
            情节ID
        """
        self._cleanup_old_episodes()

        episode_id = f"ep_{self.episode_counter}"
        self.episode_counter += 1

        episode = Episode(
            id=episode_id,
            user_input=user_input,
            agent_response=agent_response,
            success=success,
            execution_time=execution_time,
            plan_id=plan_id,
            metadata=metadata or {},
            tags=tags or [],
            importance=max(0.0, min(1.0, importance)),
        )

        self.episodes[episode_id] = episode
        self._save_to_disk()

        return episode_id

    def get(self, episode_id: str) -> Optional[Episode]:
        """
        根据ID获取情节

        Args:
            episode_id: 情节ID

        Returns:
            情节或None
        """
        return self.episodes.get(episode_id)

    def get_recent(self, count: int = 10) -> List[Episode]:
        """
        获取最近的情节

        Args:
            count: 获取数量

        Returns:
            情节列表
        """
        sorted_episodes = sorted(self.episodes.values(), key=lambda x: x.timestamp, reverse=True)
        return sorted_episodes[:count]

    def search(
        self,
        query: str,
        limit: int = 20,
        min_importance: float = 0.0,
        only_successful: bool = False,
    ) -> List[Episode]:
        """
        搜索情节记忆

        Args:
            query: 搜索关键词
            limit: 返回数量限制
            min_importance: 最小重要性
            only_successful: 只返回成功的情节

        Returns:
            匹配的情节列表
        """
        results = []
        query_lower = query.lower()

        for episode in self.episodes.values():
            if only_successful and not episode.success:
                continue

            if episode.importance < min_importance:
                continue

            if (
                query_lower in episode.user_input.lower()
                or query_lower in episode.agent_response.lower()
                or any(query_lower in tag.lower() for tag in episode.tags)
            ):
                results.append(episode)

        # 按时间倒序排列
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    def get_by_tag(self, tag: str, limit: int = 50) -> List[Episode]:
        """
        根据标签获取情节

        Args:
            tag: 标签
            limit: 返回数量限制

        Returns:
            情节列表
        """
        results = [episode for episode in self.episodes.values() if tag in episode.tags]
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    def get_failed_episodes(self, count: int = 20) -> List[Episode]:
        """
        获取失败的情节

        Args:
            count: 返回数量限制

        Returns:
            失败的情节列表
        """
        failed = [episode for episode in self.episodes.values() if not episode.success]
        failed.sort(key=lambda x: x.timestamp, reverse=True)
        return failed[:count]

    def add_tags(self, episode_id: str, tags: List[str]):
        """
        为情节添加标签

        Args:
            episode_id: 情节ID
            tags: 标签列表
        """
        if episode_id in self.episodes:
            self.episodes[episode_id].tags.extend(tags)
            # 去重
            self.episodes[episode_id].tags = list(set(self.episodes[episode_id].tags))
            self._save_to_disk()

    def set_importance(self, episode_id: str, importance: float):
        """
        设置情节重要性

        Args:
            episode_id: 情节ID
            importance: 重要性评分 (0-1)
        """
        if episode_id in self.episodes:
            self.episodes[episode_id].importance = max(0.0, min(1.0, importance))
            self._save_to_disk()

    def remove(self, episode_id: str) -> bool:
        """
        删除情节

        Args:
            episode_id: 情节ID

        Returns:
            是否删除成功
        """
        if episode_id in self.episodes:
            del self.episodes[episode_id]
            self._save_to_disk()
            return True
        return False

    def clear(self):
        """清空所有情节"""
        self.episodes.clear()
        self._save_to_disk()

    def size(self) -> int:
        """获取情节数量"""
        return len(self.episodes)

    def _cleanup_old_episodes(self):
        """清理旧的情节以保持在最大容量内"""
        if len(self.episodes) >= self.max_episodes:
            # 按重要性和时间排序，保留最重要和最新的
            sorted_episodes = sorted(
                self.episodes.values(),
                key=lambda x: (x.importance, x.timestamp),
                reverse=True,
            )
            # 保留前90%
            keep_count = int(self.max_episodes * 0.9)
            keep_episodes = sorted_episodes[:keep_count]

            self.episodes = {ep.id: ep for ep in keep_episodes}

    def _load_from_disk(self):
        """从磁盘加载记忆"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for ep_data in data.get("episodes", []):
                episode = Episode(
                    id=ep_data["id"],
                    user_input=ep_data["user_input"],
                    agent_response=ep_data["agent_response"],
                    timestamp=datetime.fromisoformat(ep_data["timestamp"]),
                    success=ep_data.get("success", True),
                    execution_time=ep_data.get("execution_time", 0.0),
                    plan_id=ep_data.get("plan_id"),
                    metadata=ep_data.get("metadata", {}),
                    tags=ep_data.get("tags", []),
                    importance=ep_data.get("importance", 0.5),
                )
                self.episodes[episode.id] = episode

            self.episode_counter = data.get("episode_counter", len(self.episodes))

        except Exception:
            pass

    def _save_to_disk(self):
        """保存记忆到磁盘"""
        if not self.storage_path:
            return

        # 确保目录存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "episode_counter": self.episode_counter,
            "episodes": [
                {
                    "id": ep.id,
                    "user_input": ep.user_input,
                    "agent_response": ep.agent_response,
                    "timestamp": ep.timestamp.isoformat(),
                    "success": ep.success,
                    "execution_time": ep.execution_time,
                    "plan_id": ep.plan_id,
                    "metadata": ep.metadata,
                    "tags": ep.tags,
                    "importance": ep.importance,
                }
                for ep in self.episodes.values()
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
        total = len(self.episodes)
        if total == 0:
            return {"total_episodes": 0}

        successful = sum(1 for ep in self.episodes.values() if ep.success)
        avg_execution_time = (
            sum(ep.execution_time for ep in self.episodes.values()) / total
        )
        avg_importance = sum(ep.importance for ep in self.episodes.values()) / total

        # 统计标签分布
        tag_counts: Dict[str, int] = {}
        for ep in self.episodes.values():
            for tag in ep.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_episodes": total,
            "successful_episodes": successful,
            "success_rate": successful / total,
            "average_execution_time": avg_execution_time,
            "average_importance": avg_importance,
            "tag_distribution": tag_counts,
            "max_capacity": self.max_episodes,
        }
