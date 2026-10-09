"""pytest 共享配置。

为 API 测试提供一个隔离的内存 SQLite 数据库，
并通过依赖覆盖让应用使用该测试库，避免污染真实的 wiki.db。
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """提供隔离测试库的 API 客户端。

    测试期间关闭后台任务处理器（worker_enabled=False），
    避免后台线程访问真实数据库、产生状态竞态；任务逻辑通过直接调用 service 验证。
    """
    original_worker = settings.worker_enabled
    settings.worker_enabled = False

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        settings.worker_enabled = original_worker


@pytest.fixture()
def db_session(client: TestClient) -> Generator[Session, None, None]:
    """提供与 client 同一测试库的会话，便于测试中直接调用 service。

    与 API 请求共用同一内存数据库语义。
    """
    gen = app.dependency_overrides[get_db]()
    try:
        yield next(gen)
    finally:
        gen.close()
