"""模型配置接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.responses import success
from app.repositories.model_config import ModelConfigRepository
from app.schemas.common import ApiResponse
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigRead,
    ModelConfigTestResult,
    ModelConfigUpdate,
)
from app.services.model_config import ModelConfigService

router = APIRouter(prefix="/model-configs", tags=["model-configs"])

logger = get_logger(__name__)


def _service(db: Session = Depends(get_db)) -> ModelConfigService:
    return ModelConfigService(db)


@router.get("", response_model=ApiResponse[list[ModelConfigRead]])
def list_model_configs(
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[list[ModelConfigRead]]:
    """查询全部模型配置（不返回 API Key 明文）。"""
    return success(data=service.list(), message="ok")


@router.post("", response_model=ApiResponse[ModelConfigRead])
def create_model_config(
    payload: ModelConfigCreate,
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[ModelConfigRead]:
    """创建模型配置。"""
    return success(data=service.create(payload), message="创建成功")


@router.get("/default", response_model=ApiResponse[ModelConfigRead | None])
def get_default_model_config(
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[ModelConfigRead | None]:
    """查询默认模型配置（可能为空）。"""
    return success(data=service.get_default(), message="ok")


@router.get("/{config_id}", response_model=ApiResponse[ModelConfigRead])
def get_model_config(
    config_id: int,
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[ModelConfigRead]:
    """查询单个模型配置。"""
    return success(data=service.get(config_id), message="ok")


@router.put("/{config_id}", response_model=ApiResponse[ModelConfigRead])
def update_model_config(
    config_id: int,
    payload: ModelConfigUpdate,
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[ModelConfigRead]:
    """更新模型配置。"""
    return success(data=service.update(config_id, payload), message="更新成功")


@router.delete("/{config_id}", response_model=ApiResponse[dict])
def delete_model_config(
    config_id: int,
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[dict]:
    """删除模型配置。"""
    service.delete(config_id)
    return success(data={"id": config_id}, message="删除成功")


@router.post("/{config_id}/test", response_model=ApiResponse[ModelConfigTestResult])
def test_model_config(
    config_id: int,
    service: ModelConfigService = Depends(_service),
) -> ApiResponse[ModelConfigTestResult]:
    """测试指定模型配置的连接可用性。"""
    return success(data=service.test_connection(config_id), message="测试完成")
