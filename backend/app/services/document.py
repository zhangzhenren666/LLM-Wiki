"""文档导入业务逻辑层。"""
import logging
import os
import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.models.document import Document, ImportStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.wiki_page import PageStatus
from app.repositories import page as page_repo
from app.repositories.document_task import DocumentTaskRepository
from app.services import page as page_service
from app.services.document_task import DocumentTaskService
from app.worker import processor

logger = logging.getLogger("app.services.document")

ALLOWED_EXTENSIONS = {".md", ".txt", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# 提取第一个 Markdown 一级标题
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _get_upload_dir() -> Path:
    """获取配置化的上传目录。"""
    return Path(settings.upload_dir)


def _generate_dest_path(safe_name: str) -> Path:
    """为文件名生成唯一的目标路径，避免覆盖已有文件。"""
    upload_dir = _get_upload_dir()
    base, ext_part = os.path.splitext(safe_name)
    dest_path = upload_dir / safe_name
    counter = 1
    while dest_path.exists():
        dest_path = upload_dir / f"{base}_{counter}{ext_part}"
        counter += 1
    return dest_path


def _extract_title_from_markdown(content: str, fallback: str) -> str:
    """从 Markdown 内容提取一级标题，无标题则用 fallback。"""
    m = _HEADING_RE.search(content)
    return m.group(1).strip() if m else fallback


def _extract_text_from_docx(file_path: str) -> tuple[str, str]:
    """从 .docx 提取文本内容和标题。"""
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    paragraphs: list[str] = []
    title: str | None = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # 尝试从样式判断标题
        if para.style and para.style.name and "heading" in para.style.name.lower():
            if title is None:
                title = text
            paragraphs.append(f"## {text}")
        else:
            paragraphs.append(text)

    content = "\n\n".join(paragraphs)
    return content, title


def _sanitize_filename(filename: str) -> str:
    """清理文件名，防止路径穿越和非法字符。"""
    # 只保留文件名，去掉路径
    name = Path(filename).name
    # 替换非法字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # 限制长度
    if len(name) > 200:
        base, ext = os.path.splitext(name)
        name = base[:200 - len(ext)] + ext
    return name or "unnamed"


def upload_document(
    db: Session,
    file: UploadFile,
    knowledge_base_id: int,
    *,
    request_id: str | None = None,
    max_attempts: int | None = None,
) -> Document:
    """上传文档并导入为 Wiki 页面。

    步骤：
    1. 校验知识库
    2. 校验文件类型和大小
    3. 安全处理文件名
    4. 解析内容（md/txt 在内存中先解析；docx 需先写临时文件）
    5. 内容校验通过后保存原始文件
    6. 创建 Wiki 页面并记录导入状态
    7. 创建 AI 处理任务并投递后台执行

    幂等：request_id 存在时返回上次已创建的文档，避免重复上传产生重复任务。
    """
    # 0. 幂等：同一 request_id 的重复请求直接返回已存在文档
    if request_id:
        existing_task = DocumentTaskRepository(db).get_by_request_id(request_id)
        if existing_task is not None:
            existing_doc = db.get(Document, existing_task.document_id)
            if existing_doc is not None:
                return existing_doc

    # 1. 校验知识库
    kb = db.get(KnowledgeBase, knowledge_base_id)
    if kb is None:
        raise NotFoundError(f"知识库不存在: id={knowledge_base_id}")

    filename = file.filename or "unnamed"

    # 2. 校验扩展名
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            f"不支持的文件类型: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            code=400,
            status_code=400,
        )

    # 3. 读取内容并校验大小
    content_bytes = file.file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise AppError(
            f"文件大小超过限制 ({MAX_FILE_SIZE // (1024*1024)} MB)",
            code=400,
            status_code=400,
        )

    safe_name = _sanitize_filename(filename)
    base, ext_part = os.path.splitext(safe_name)

    # 4. 内容解析（优先内存解析，docx 需写临时文件）
    dest_path: Path | None = None
    try:
        content: str
        title: str

        if ext == ".md":
            raw = content_bytes.decode("utf-8")
            title = _extract_title_from_markdown(raw, base)
            content = raw
        elif ext == ".txt":
            raw = content_bytes.decode("utf-8")
            title = base
            content = raw
        elif ext == ".docx":
            # docx 必须先写盘才能解析（python-docx 限制）
            upload_dir = _get_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest_path = _generate_dest_path(safe_name)
            dest_path.write_bytes(content_bytes)
            content, extracted_title = _extract_text_from_docx(str(dest_path))
            title = extracted_title or base
        else:
            raise AppError(f"不支持的文件类型: {ext}", code=400, status_code=400)

        # 5. 内容校验通过后，md/txt 保存文件到磁盘
        if ext in (".md", ".txt"):
            upload_dir = _get_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest_path = _generate_dest_path(safe_name)
            dest_path.write_bytes(content_bytes)

        # 6. 创建 Wiki 页面
        page = page_service.create_page(
            db,
            knowledge_base_id=knowledge_base_id,
            title=title,
            slug=None,
            content=content,
            parent_id=None,
            status=PageStatus.DRAFT,
        )

        # 7. 记录导入成功（存储相对路径，避免泄露服务器目录结构）
        relative_path = str(dest_path) if dest_path else safe_name
        doc = Document(
            knowledge_base_id=knowledge_base_id,
            file_name=safe_name,
            file_type=ext,
            file_path=relative_path,
            page_id=page.id,
            import_status=ImportStatus.SUCCESS,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # 7. 创建 AI 处理任务并投递后台执行（上传不等待模型处理；
        #    任务创建失败不阻断导入，仅记录日志）
        try:
            task = DocumentTaskService(db).create_task_for_document(
                document_id=doc.id,
                knowledge_base_id=knowledge_base_id,
                request_id=request_id or None,  # 空字符串 → None，避免 UNIQUE 冲突
                max_attempts=max_attempts or settings.task_max_attempts,
            )
            db.commit()
            processor.enqueue(task.id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "文档处理任务创建失败（导入仍成功） document_id=%s",
                doc.id,
            )

        return doc

    except AppError:
        raise
    except Exception as e:
        logger.exception("文档导入失败: %s", safe_name)
        # 记录失败（存储相对路径）
        relative_path = str(dest_path) if dest_path else safe_name
        doc = Document(
            knowledge_base_id=knowledge_base_id,
            file_name=safe_name,
            file_type=ext,
            file_path=relative_path,
            import_status=ImportStatus.FAILED,
            error_message=str(e)[:500],
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        raise AppError(f"文档解析失败: {e}", code=500, status_code=500)