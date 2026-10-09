"""轻量后台任务处理器。

采用进程内线程 + 内存队列（标准库 queue/threading），不引入消息中间件，
与项目规模相称。负责：
1. 消费上传后入队的文档处理任务；
2. 启动时恢复长时间卡在 processing 的中断任务。

每个任务在独立的数据库会话中执行，避免与请求会话耦合；
SQLite 文件库（生产）支持多线程访问。
"""
import queue
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.services.document_task import DocumentTaskService

logger = get_logger(__name__)


class TaskProcessor:
    """文档处理任务后台处理器（进程内单例）。"""

    def __init__(self) -> None:
        self._queue: "queue.Queue[int]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._session_factory = None

    # ---------- 生命周期 ----------

    def start(self) -> None:
        """启动后台工作线程（受 settings.worker_enabled 控制）。"""
        if not settings.worker_enabled:
            logger.info("后台任务处理器已禁用（worker_enabled=False）")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="doc-task-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("后台任务处理器已启动")

    def stop(self) -> None:
        """请求停止后台工作线程。"""
        self._stop.set()
        logger.info("后台任务处理器停止请求已发出")

    # ---------- 对外接口 ----------

    def enqueue(self, task_id: int) -> None:
        """将任务加入处理队列。"""
        self._queue.put(task_id)

    def recover_interrupted(self) -> int:
        """立即恢复中断任务（生产在 worker 启动时调用，便于测试可手动触发）。"""
        db = self._get_session()
        try:
            return DocumentTaskService(db).recover_interrupted(
                settings.task_processing_timeout
            )
        finally:
            db.close()

    # ---------- 内部实现 ----------

    def _get_session_factory(self):
        if self._session_factory is None:
            engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
            )
            self._session_factory = sessionmaker(
                bind=engine, expire_on_commit=False
            )
        return self._session_factory

    def _get_session(self):
        return self._get_session_factory()()

    def _run(self) -> None:
        """工作线程主循环。"""
        self.recover_interrupted()
        while not self._stop.is_set():
            try:
                task_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._process(task_id)
            except Exception:  # noqa: BLE001 - 单任务失败不能拖垮线程
                logger.exception("后台任务处理异常 task_id=%s", task_id)

    def _process(self, task_id: int) -> None:
        """在独立会话中执行单任务。"""
        db = self._get_session()
        try:
            try:
                DocumentTaskService(db).process_task(task_id)
            except AppError:
                # 幂等冲突（已完成/处理中等）直接忽略，属预期
                logger.info("任务被跳过 task_id=%s（状态不允许重复执行）", task_id)
        finally:
            db.close()


# 进程内单例
processor = TaskProcessor()
