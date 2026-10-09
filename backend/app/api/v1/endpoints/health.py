"""健康检查相关接口。"""
from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import get_logger
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.health import HealthData

router = APIRouter(tags=["health"])

logger = get_logger(__name__)


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check() -> ApiResponse[HealthData]:
    """健康检查接口。"""
    data = HealthData(status="ok", version=settings.app_version)
    logger.debug("健康检查被调用")
    return success(data=data, message="Wiki 知识库后端运行正常")
