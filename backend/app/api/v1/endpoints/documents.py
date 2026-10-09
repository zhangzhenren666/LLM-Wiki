"""文档导入 API 接口。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.document import DocumentRead
from app.services import document as document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=ApiResponse[DocumentRead])
async def upload_document(
    knowledge_base_id: int = Form(..., description="目标知识库 ID"),
    file: UploadFile = File(..., description="上传文件 (.md/.txt/.docx)"),
    request_id: str | None = Form(None, description="可选幂等请求 ID，重复请求不会重复创建任务"),
    db: Session = Depends(get_db),
):
    """上传文档并导入为 Wiki 页面，并自动创建 AI 处理任务。"""
    doc = document_service.upload_document(
        db, file, knowledge_base_id, request_id=request_id
    )
    return success(data=DocumentRead.model_validate(doc), message="导入成功")