"""文档处理任务接口。"""
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.models import TaskStatus
from app.schemas.common import ApiResponse
from app.schemas.document_task import DocumentTaskListItem, DocumentTaskRead
from app.services.document_task import DocumentTaskService

router = APIRouter(prefix="/document-tasks", tags=["document-tasks"])


def _service(db: Session = Depends(get_db)) -> DocumentTaskService:
    return DocumentTaskService(db)


ValidStatus = Literal[
    "pending", "processing", "completed", "failed", "needs_attention"
]


@router.get("", response_model=ApiResponse[list[DocumentTaskListItem]])
def list_document_tasks(
    status: ValidStatus | None = None,
    knowledge_base_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    service: DocumentTaskService = Depends(_service),
) -> ApiResponse[list[DocumentTaskListItem]]:
    """查询文档处理任务列表，可按状态/知识库过滤。"""
    status_enum = TaskStatus(status) if status else None
    tasks = service.list_tasks(
        status=status_enum,
        knowledge_base_id=knowledge_base_id,
        limit=limit,
        offset=offset,
    )
    return success(
        data=[service.to_list_item(t) for t in tasks], message="ok"
    )


@router.get("/{task_id}", response_model=ApiResponse[DocumentTaskRead])
def get_document_task(
    task_id: int,
    service: DocumentTaskService = Depends(_service),
) -> ApiResponse[DocumentTaskRead]:
    """查询任务详情（含处理记录步骤）。"""
    task = service.get_task(task_id)
    return success(data=service.to_read(task), message="ok")


@router.post("/{task_id}/retry", response_model=ApiResponse[DocumentTaskRead])
def retry_document_task(
    task_id: int,
    service: DocumentTaskService = Depends(_service),
) -> ApiResponse[DocumentTaskRead]:
    """重试失败（或需关注）的任务。"""
    task = service.retry_task(task_id)
    return success(data=service.to_read(task), message="已进入待处理，等待重新执行")
