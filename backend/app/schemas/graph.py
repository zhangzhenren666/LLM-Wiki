"""知识图谱 Pydantic 模型。"""
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """图谱节点。"""

    id: int = Field(..., description="页面 ID")
    label: str = Field(..., description="显示标签（标题）")
    title: str = Field(..., description="页面标题")
    slug: str = Field(..., description="URL 标识")
    knowledge_base_id: int = Field(..., description="所属知识库 ID")


class GraphEdge(BaseModel):
    """图谱边。"""

    id: int = Field(..., description="关系 ID")
    source: int = Field(..., description="源节点 ID")
    target: int = Field(..., description="目标节点 ID")
    relation_type: str = Field(..., description="关系类型（枚举值：link/reference/related 等）")
    label: str = Field(..., description="关系类型展示标签（中文）")


class GraphResponse(BaseModel):
    """图谱响应。"""

    nodes: list[GraphNode] = Field(default_factory=list, description="节点列表")
    edges: list[GraphEdge] = Field(default_factory=list, description="边列表")