"""健康检查及统一响应格式测试。"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_root() -> None:
    """测试根路径 /health 返回统一响应格式。"""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "ok"
    assert "version" in data["data"]


def test_health_v1() -> None:
    """测试 v1 路由 /api/v1/health。"""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "ok"
