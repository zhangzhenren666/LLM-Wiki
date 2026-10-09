"""文档处理任务数据访问层。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import DocumentTask, KnowledgeItemStatus, TaskStatus


class DocumentTaskRepository:
    """文档处理任务仓储。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def _with_steps(self, query):
        """预加载任务步骤，避免 N+1。"""
        return query.options(selectinload(DocumentTask.steps))

    def get(self, task_id: int) -> DocumentTask | None:
        """按主键查询（含步骤）。"""
        stmt = self._with_steps(
            select(DocumentTask).where(DocumentTask.id == task_id)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_document(self, document_id: int) -> DocumentTask | None:
        """按文档 id 查询任务（含步骤）。"""
        stmt = self._with_steps(
            select(DocumentTask).where(DocumentTask.document_id == document_id)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_request_id(self, request_id: str) -> DocumentTask | None:
        """按幂等请求 ID 查询。"""
        stmt = self._with_steps(
            select(DocumentTask).where(DocumentTask.request_id == request_id)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        status: TaskStatus | None = None,
        knowledge_base_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DocumentTask]:
        """查询任务列表，支持按状态/知识库过滤，默认新任务在前。"""
        stmt = select(DocumentTask)
        if status is not None:
            stmt = stmt.where(DocumentTask.status == status)
        if knowledge_base_id is not None:
            stmt = stmt.where(
                DocumentTask.knowledge_base_id == knowledge_base_id
            )
        stmt = stmt.order_by(DocumentTask.id.desc()).limit(limit).offset(offset)
        return list(self._db.execute(stmt).scalars())

    def list_processing_stuck(
        self, timeout_seconds: int
    ) -> list[DocumentTask]:
        """查询长时间处于 processing 未及时更新的任务（中断候选）。"""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        stmt = (
            select(DocumentTask)
            .where(
                DocumentTask.status == TaskStatus.PROCESSING,
                DocumentTask.started_at < cutoff,
            )
            .order_by(DocumentTask.id)
        )
        return list(self._db.execute(stmt).scalars())

    def create(
        self,
        *,
        document_id: int,
        knowledge_base_id: int,
        request_id: str | None,
        max_attempts: int,
    ) -> DocumentTask:
        """创建任务（待处理）。"""
        task = DocumentTask(
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
            request_id=request_id,
            status=TaskStatus.PENDING,
            attempts=0,
            progress=0,
            max_attempts=max_attempts,
        )
        self._db.add(task)
        self._db.flush()
        return task

    def mark_processing(self, task: DocumentTask) -> None:
        """标记为处理中（尝试次数 +1 并记录开始时间）。"""
        task.status = TaskStatus.PROCESSING
        task.attempts += 1
        task.started_at = datetime.now(timezone.utc)
        task.progress = 5
        task.finished_at = None
        task.error_message = None
        self._db.flush()

    def mark_completed(self, task: DocumentTask, progress: int = 100) -> None:
        """标记为已完成。"""
        task.status = TaskStatus.COMPLETED
        task.progress = progress
        task.finished_at = datetime.now(timezone.utc)
        task.error_message = None
        self._db.flush()

    def mark_failed(
        self, task: DocumentTask, error: str, progress: int = 0
    ) -> None:
        """标记为失败，记录可读原因（不写入完整文档正文）。"""
        task.status = TaskStatus.FAILED
        task.progress = progress
        task.finished_at = datetime.now(timezone.utc)
        task.error_message = (error or "")[:2000]
        self._db.flush()

    def reset_for_retry(self, task: DocumentTask) -> None:
        """将可重试任务重置为待处理。"""
        task.status = TaskStatus.PENDING
        task.progress = 0
        task.started_at = None
        task.finished_at = None
        task.error_message = None
        self._db.flush()

    def update_interrupted(
        self, task: DocumentTask, error: str
    ) -> None:
        """将中断（卡在 processing）的任务标记为失败。"""
        task.status = TaskStatus.FAILED
        task.finished_at = datetime.now(timezone.utc)
        task.error_message = (error or "")[:2000]
        self._db.flush()

    def bulk_reset_stuck(self, timeout_seconds: int) -> int:
        """将超过阈值的 processing 任务批量重置为失败（用于启动恢复）。"""
        stuck = self.list_processing_stuck(timeout_seconds)
        for task in stuck:
            self.update_interrupted(
                task, "服务重启时任务中断，已标记为异常，可手动重试"
            )
        return len(stuck)

    def mark_needs_attention(
        self, task: DocumentTask, error: str, progress: int = 90
    ) -> None:
        """标记为需要关注（部分知识条目存在异常）。"""
        task.status = TaskStatus.NEEDS_ATTENTION
        task.progress = progress
        task.finished_at = datetime.now(timezone.utc)
        task.error_message = (error or "")[:2000]
        self._db.flush()

    def delete(self, task: DocumentTask) -> None:
        """删除任务。"""
        self._db.delete(task)
        self._db.flush()
