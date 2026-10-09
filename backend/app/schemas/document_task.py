"""文档处理任务 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskStepRead(BaseModel):
    """处理记录步骤响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    step_name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    page_id: int | None
    relation_id: int | None
    created_at: datetime


class DocumentTaskRead(BaseModel):
    """文档处理任务响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    knowledge_base_id: int
    request_id: str | None
    status: str
    attempts: int
    max_attempts: int
    progress: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    steps: list[TaskStepRead] = []


class DocumentTaskListItem(BaseModel):
    """任务列表项（不含步骤，轻量）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    knowledge_base_id: int
    request_id: str | None
    status: str
    attempts: int
    max_attempts: int
    progress: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
