"""应用配置模块。

从环境变量 / .env 文件中读取配置，供应用各处使用。
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置。"""

    app_name: str = "Wiki 知识库后端"
    app_version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"

    cors_origins: List[str] = ["http://localhost:3000"]

    database_url: str = "sqlite:///./wiki.db"

    # 文件上传目录（相对或绝对路径）
    upload_dir: str = "uploads"

    # ------ 文档处理任务后台 ------
    # 是否启用后台任务处理器（测试环境通常关闭，改为手动触发）
    worker_enabled: bool = True
    # 单任务最大执行次数（含重试）
    task_max_attempts: int = 3
    # 超过该时长仍处于 processing 视为中断（秒），服务重启时用于恢复
    task_processing_timeout: int = 300

    # ------ 权限扩展预留（当前未实现认证） ------
    # JWT 签名密钥
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    # JWT 算法
    jwt_algorithm: str = "HS256"
    # Token 过期时间（分钟）
    jwt_expire_minutes: int = 60 * 24  # 24 小时

    # ------ 大模型 API Key 加密 ------
    # 用于加密存储模型配置中的 API Key。生产环境必须通过环境变量设置为随机值。
    # 若未设置，则从 jwt_secret 派生（仅便于开发/测试，生产请务必显式配置）。
    model_api_key_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()


settings = get_settings()
