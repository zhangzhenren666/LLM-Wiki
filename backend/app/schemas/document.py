"""文档导入 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """文档响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    file_name: str
    file_type: str | None
    import_status: str
    page_id: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime