"""Wiki 知识库后端应用入口。

启动方式：
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import install_exception_handlers
from app.core.logger import get_logger, setup_logging
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.health import HealthData
from app.worker import processor

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动/停止轻量后台任务处理器。

    处理器启动时会恢复上次中断的文档处理任务。
    worker_enabled=False 时（如测试）不会真正启动后台线程。
    """
    processor.start()
    yield
    processor.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 LLM-Wiki 理念的 Markdown 知识库管理系统后端",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 跨域配置，允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一异常处理器（须在路由挂载前调用）
install_exception_handlers(app)

# 挂载 v1 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=ApiResponse[HealthData])
def root_health() -> ApiResponse[HealthData]:
    """根路径健康检查。"""
    logger.debug("根路径健康检查被调用")
    data = HealthData(status="ok", version=settings.app_version)
    return success(data=data, message="Wiki 知识库后端运行正常")
