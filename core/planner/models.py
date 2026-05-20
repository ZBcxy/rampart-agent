from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PlanNode(BaseModel):
    """
    计划树节点
    """

    id: str = Field(..., description="节点唯一标识")
    type: Literal["action", "branch", "parallel", "human"] = Field(..., description="节点类型")
    content: str = Field(..., description="节点内容（工具调用描述或分支条件）")
    children: List["PlanNode"] = Field(default_factory=list, description="子节点列表")
    fallback: Optional[str] = Field(None, description="失败回退路径")
    priority: int = Field(1, description="优先级（数值越小优先级越高）")
    confidence: float = Field(0.5, description="置信度（0-1）")


PlanNode.model_rebuild()


class PlanRevision(BaseModel):
    """
    计划修订记录
    """

    revision_id: str = Field(..., description="修订ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="修订时间")
    reason: str = Field(..., description="修订原因")
    old_plan: Optional[str] = Field(None, description="旧计划ID")
    new_plan: str = Field(..., description="新计划ID")


class PlanTree(BaseModel):
    """
    执行计划树
    """

    id: str = Field(..., description="计划唯一标识")
    root: PlanNode = Field(..., description="根节点")
    confidence: float = Field(0.5, description="整体置信度")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    revision_history: List[PlanRevision] = Field(default_factory=list, description="修订历史")

    def add_revision(self, reason: str, new_plan_id: str):
        """
        添加修订记录
        """
        revision = PlanRevision(
            revision_id=f"rev-{datetime.now().timestamp()}", reason=reason, old_plan=self.id, new_plan=new_plan_id
        )
        self.revision_history.append(revision)
        self.id = new_plan_id


class ExecutionObservation(BaseModel):
    """
    执行观察结果
    """

    node_id: str = Field(..., description="节点ID")
    success: bool = Field(..., description="执行是否成功")
    result: Optional[dict] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="执行时间")
    deviation: float = Field(0.0, description="与预期的偏差值")
