"""数据库连接与会话管理。

统一管理 SQLAlchemy engine / Session，业务代码不应直接创建连接，
应通过 get_db 依赖或 SessionLocal 获取会话。
"""
from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


@dataclass
class AuthUser:
    """当前请求的用户上下文。

    权限扩展预留：目前 user_id 始终为 None（匿名）。
    后续接入 JWT/OAuth 后在 get_current_user 中解析真实用户。
    """

    user_id: int | None = None


def _build_engine():
    """根据配置构建 engine。

    SQLite 需要 check_same_thread=False 以便在 FastAPI 多线程下使用。
    """
    database_url = settings.database_url
    connect_args = {}
    if database_url.startswith("sqlite"):
        # SQLite 在 Windows/多线程下需要关闭同一线程检查
        connect_args = {"check_same_thread": False}

    kwargs = {"url": database_url, "connect_args": connect_args}
    # SQLite 无需连接池；预留 PostgreSQL 时可启用连接池参数
    if not database_url.startswith("sqlite"):
        kwargs["pool_pre_ping"] = True

    return create_engine(**kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供一个数据库会话并在请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user() -> AuthUser:
    """权限扩展预留：获取当前用户上下文。

    当前始终返回匿名用户（user_id=None）。
    后续接入认证后在此解析 JWT/Session 并返回真实用户。
    用法：在路由中增加 `current_user: AuthUser = Depends(get_current_user)`。
    """
    return AuthUser(user_id=None)


def init_db() -> None:
    """初始化数据库：创建所有表。

    用于测试与首次启动；正式迁移请使用 Alembic。
    """
    from app import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)
