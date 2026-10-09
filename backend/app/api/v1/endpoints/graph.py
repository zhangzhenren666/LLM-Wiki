"""知识图谱 API 接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.graph import GraphResponse
from app.services import graph as graph_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/pages/{page_id}", response_model=ApiResponse[GraphResponse])
def get_page_graph(
    page_id: int,
    depth: int = Query(1, ge=1, le=5, description="图谱深度（暂仅支持 1）"),
    db: Session = Depends(get_db),
):
    """获取单页面的关联图谱（1-hop 邻域）。"""
    result = graph_service.get_page_graph(db, page_id, depth=depth)
    return success(data=result, message="ok")


@router.get("/knowledge-bases/{kb_id}", response_model=ApiResponse[GraphResponse])
def get_kb_graph(
    kb_id: int,
    max_nodes: int | None = Query(
        None, ge=1, description="节点数量上限，不传则返回全部"
    ),
    db: Session = Depends(get_db),
):
    """获取知识库整体图谱，可按 max_nodes 限制规模。"""
    result = graph_service.get_kb_graph(db, kb_id, max_nodes=max_nodes)
    return success(data=result, message="ok")