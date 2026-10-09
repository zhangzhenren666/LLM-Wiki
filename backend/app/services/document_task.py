"""文档处理任务业务逻辑层。

执行器 `process_task` 按顺序执行：
1. 解析步骤（确认文档正文可读）
2. AI 知识提取步骤（调用模型提取知识并自动创建 Wiki 页面）
3. 关系构建步骤（自动识别新页面与现有页面的关系）
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.logger import get_logger
from app.models import DocumentTask, KnowledgeItemStatus, StepStatus, TaskStatus, TaskStep
from app.repositories.document_task import DocumentTaskRepository
from app.schemas.document_task import DocumentTaskRead, DocumentTaskListItem
from app.services.knowledge_extraction import KnowledgeExtractionService
from app.services.relation_extraction import RelationExtractionService

logger = get_logger(__name__)

# 步骤名称
STEP_PARSE = "解析文档"
STEP_AI_EXTRACT = "AI知识提取"
STEP_RELATION = "关系构建"


class DocumentTaskService:
    """文档处理任务业务服务。"""

    def __init__(self, db: Session) -> None:
        self._repo = DocumentTaskRepository(db)
        self._db = db

    # ---------- 创建与查询 ----------

    def create_task_for_document(
        self,
        document_id: int,
        knowledge_base_id: int,
        *,
        request_id: str | None = None,
        max_attempts: int,
    ) -> DocumentTask:
        """为文档创建处理任务（待处理）。

        轻量幂等：同一 request_id 已存在任务时直接返回，避免重复提交产生重复任务。
        document_id 唯一约束也从数据库层面保证一个文档只有一个处理任务。
        重复请求会抛出冲突，由调用方决定返回已有任务。
        """
        request_id = request_id or None  # 空字符串 → None，避免 UNIQUE 冲突
        if request_id:
            existing = self._repo.get_by_request_id(request_id)
            if existing is not None:
                return existing

        return self._repo.create(
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
            request_id=request_id,
            max_attempts=max_attempts,
        )

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        knowledge_base_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DocumentTask]:
        """查询任务列表。"""
        return self._repo.list(
            status=status,
            knowledge_base_id=knowledge_base_id,
            limit=limit,
            offset=offset,
        )

    def get_task(self, task_id: int) -> DocumentTask:
        """查询任务详情（含处理记录步骤）。"""
        task = self._repo.get(task_id)
        if task is None:
            raise NotFoundError(f"任务不存在: id={task_id}")
        return task

    def to_read(self, task: DocumentTask) -> DocumentTaskRead:
        """转响应模型。"""
        return DocumentTaskRead.model_validate(task)

    def to_list_item(self, task: DocumentTask) -> DocumentTaskListItem:
        """转列表项模型。"""
        return DocumentTaskListItem.model_validate(task)

    # ---------- 重试 ----------

    def retry_task(self, task_id: int) -> DocumentTask:
        """重试失败（或需关注）的任务，重置为待处理供重新执行。"""
        task = self.get_task(task_id)
        if task.status not in (TaskStatus.FAILED, TaskStatus.NEEDS_ATTENTION):
            raise ConflictError(
                f"仅失败或需关注的任务可重试，当前状态: {task.status.value}"
            )
        self._repo.reset_for_retry(task)
        self._db.commit()
        self._db.refresh(task)
        return task

    # ---------- 中断恢复 ----------

    def recover_interrupted(self, timeout_seconds: int) -> int:
        """将长时间卡在 processing 的任务标记为失败（服务重启时调用）。"""
        count = self._repo.bulk_reset_stuck(timeout_seconds)
        self._db.commit()
        return count

    # ---------- 执行器 ----------

    def process_task(self, task_id: int) -> DocumentTask:
        """执行单个文档处理任务。

        pending -> processing -> completed / failed / needs_attention。
        解析 + AI 知识提取，合格条目自动创建 Wiki 页面。
        """
        task = self._repo.get(task_id)
        if task is None:
            raise AppError(
                f"任务不存在: id={task_id}", code=404, status_code=404
            )

        # 幂等保护：不重复执行正在处理中或已完成的任务
        if task.status == TaskStatus.PROCESSING:
            raise ConflictError("任务正在处理中，不能重复执行")
        if task.status == TaskStatus.COMPLETED:
            raise ConflictError("任务已完成，不能重复执行")
        if not task.max_attempts or task.attempts >= task.max_attempts:
            # 已达最大尝试次数，标记失败
            self._repo.mark_failed(task, "已达到最大重试次数")
            self._db.commit()
            return task

        self._repo.mark_processing(task)
        self._db.commit()

        try:
            extraction_stats = self._run_steps(task)
            # 根据提取统计决定最终状态
            if extraction_stats is None:
                self._repo.mark_completed(task)
            elif extraction_stats.get("needs_attention", 0) > 0 and extraction_stats.get("auto_created", 0) == 0:
                self._repo.mark_needs_attention(
                    task,
                    f"所有知识条目均需关注（needs_attention={extraction_stats['needs_attention']}, "
                    f"duplicate={extraction_stats.get('duplicate', 0)}, "
                    f"skipped={extraction_stats.get('skipped', 0)}）",
                )
            elif extraction_stats.get("needs_attention", 0) > 0 or extraction_stats.get("duplicate", 0) > 0:
                # 部分成功但存在异常条目
                self._repo.mark_completed(
                    task,
                    progress=95,
                )
                # 在 error_message 中记录异常统计（不影响 completed 状态）
                anomaly_parts = []
                if extraction_stats.get("needs_attention", 0) > 0:
                    anomaly_parts.append(f"需关注: {extraction_stats['needs_attention']}条")
                if extraction_stats.get("duplicate", 0) > 0:
                    anomaly_parts.append(f"疑似重复: {extraction_stats['duplicate']}条")
                if extraction_stats.get("skipped", 0) > 0:
                    anomaly_parts.append(f"已跳过: {extraction_stats['skipped']}条")
                # 追加关系异常信息
                if extraction_stats.get("relation_anomaly", 0) > 0:
                    anomaly_parts.append(f"关系异常: {extraction_stats['relation_anomaly']}条")
                if extraction_stats.get("relation_created", 0) > 0:
                    # 给 success 消息也追加关系信息
                    pass
                task.error_message = f"部分条目异常（已自动创建{extraction_stats.get('auto_created', 0)}个页面）- {'; '.join(anomaly_parts)}"
                self._db.flush()
            else:
                self._repo.mark_completed(task)
        except Exception as exc:  # noqa: BLE001 - 需捕获所有异常以更新任务状态
            logger.exception("任务执行失败 task_id=%s", task.id)
            self._repo.mark_failed(task, str(exc)[:500] or "处理失败")
        self._db.commit()
        self._db.refresh(task)
        return task

    def _run_steps(self, task: DocumentTask) -> dict | None:
        """执行处理步骤：解析 → AI 知识提取 → 关系构建。

        返回合并的统计 dict（包含 extraction 和 relation 结果），
        或 None（所有 AI 步骤均跳过时）。
        """
        self._run_parse_step(task)
        extraction_stats = self._run_ai_extract_step(task)
        relation_stats = self._run_relation_step(task)

        # 合并统计
        if extraction_stats is None and relation_stats is None:
            return None
        merged = dict(extraction_stats or {})
        if relation_stats:
            merged["relation_created"] = relation_stats.get("created", 0)
            merged["relation_anomaly"] = relation_stats.get("anomaly", 0)
        return merged

    def _run_parse_step(self, task: DocumentTask) -> None:
        """解析步骤：读取文档已导入的页面正文作为解析产物。"""
        step = TaskStep(
            task_id=task.id,
            step_name=STEP_PARSE,
            status=StepStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(step)
        self._db.flush()

        document = task.document
        page = document.page if document else None
        if page is None:
            step.status = StepStatus.FAILED
            step.finished_at = datetime.now(timezone.utc)
            step.error_message = "文档未生成可解析的 Wiki 页面"
            self._db.flush()
            raise RuntimeError("文档未生成可解析的 Wiki 页面")

        # 触发正文加载以确认可解析（内容不写入任何日志/记录）
        _ = page.content or ""

        step.page_id = page.id
        step.status = StepStatus.COMPLETED
        step.finished_at = datetime.now(timezone.utc)
        task.progress = 60
        self._db.flush()

    def _run_ai_extract_step(self, task: DocumentTask) -> dict | None:
        """AI 知识提取步骤：调用模型提取知识并自动创建 Wiki 页面。

        复用阶段 01 的模型配置服务和阶段 02 的任务步骤记录机制。

        返回提取统计 dict（auto_created/needs_attention/duplicate/skipped），
        无可用模型配置时返回 None（跳过提取，不视作失败）。
        """
        step = TaskStep(
            task_id=task.id,
            step_name=STEP_AI_EXTRACT,
            status=StepStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(step)
        self._db.flush()

        try:
            extraction_service = KnowledgeExtractionService(self._db)
            stats = extraction_service.extract_and_create(task)
            task.progress = 95

            if stats is None:
                # 无可用模型配置，跳过提取
                step.status = StepStatus.COMPLETED
                step.finished_at = datetime.now(timezone.utc)
                step.error_message = "未配置可用模型，跳过知识提取"
                self._db.flush()
                logger.info("AI 知识提取跳过（无模型配置） task_id=%s", task.id)
                return None

            step.status = StepStatus.COMPLETED
            step.finished_at = datetime.now(timezone.utc)

            # 记录提取统计到步骤
            parts = []
            if stats.get("auto_created", 0) > 0:
                parts.append(f"自动创建: {stats['auto_created']}个页面")
            if stats.get("needs_attention", 0) > 0:
                parts.append(f"需关注: {stats['needs_attention']}条")
            if stats.get("duplicate", 0) > 0:
                parts.append(f"疑似重复: {stats['duplicate']}条")
            if stats.get("skipped", 0) > 0:
                parts.append(f"已跳过: {stats['skipped']}条")
            if not parts:
                step.error_message = "未提取到有效知识"
            self._db.flush()

            logger.info(
                "AI 知识提取完成 task_id=%s stats=%s",
                task.id, stats,
            )
            return stats

        except Exception:
            step.status = StepStatus.FAILED
            step.finished_at = datetime.now(timezone.utc)
            logger.exception("AI 知识提取失败 task_id=%s", task.id)
            self._db.flush()
            raise

    def _run_relation_step(self, task: DocumentTask) -> dict | None:
        """关系构建步骤：自动识别新页面与现有页面的关系。

        只在 AI 提取成功创建了页面时才执行。
        返回关系统计 dict（created/anomaly/skipped），
        无新页面或无模型配置时返回 None。
        """
        step = TaskStep(
            task_id=task.id,
            step_name=STEP_RELATION,
            status=StepStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(step)
        self._db.flush()

        try:
            relation_service = RelationExtractionService(self._db)
            stats = relation_service.extract_and_create_relations(task)
            task.progress = 100

            step.status = StepStatus.COMPLETED
            step.finished_at = datetime.now(timezone.utc)

            # 记录结果统计到步骤
            parts = []
            if stats.get("created", 0) > 0:
                parts.append(f"自动创建: {stats['created']}条关系")
            if stats.get("anomaly", 0) > 0:
                parts.append(f"异常: {stats['anomaly']}条")
            if stats.get("skipped", 0) > 0:
                parts.append(f"跳过: {stats['skipped']}个页面")
            if not parts:
                step.error_message = "无新页面或无可识别关系"
            self._db.flush()

            logger.info(
                "关系构建完成 task_id=%s stats=%s",
                task.id, stats,
            )
            return stats

        except Exception:
            step.status = StepStatus.FAILED
            step.finished_at = datetime.now(timezone.utc)
            logger.exception("关系构建失败 task_id=%s", task.id)
            self._db.flush()
            raise
