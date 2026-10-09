"""统一异常处理测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppError,
    NotFoundError,
    install_exception_handlers,
)


def create_test_app() -> FastAPI:
    """构建一个用于测试异常处理的独立应用。"""
    test_app = FastAPI()

    @test_app.get("/ok")
    def ok() -> dict:
        return {"status": "ok"}

    @test_app.get("/error")
    def error() -> None:
        raise AppError("业务错误", code=1001, status_code=400)

    @test_app.get("/not-found")
    def not_found() -> None:
        raise NotFoundError()

    @test_app.post("/validate")
    async def validate(item: int) -> dict:
        return {"item": item}

    install_exception_handlers(test_app)
    return test_app


client = TestClient(create_test_app())


def test_app_error() -> None:
    """测试业务异常返回统一错误格式。"""
    res = client.get("/error")
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == 1001
    assert data["message"] == "业务错误"


def test_not_found_error() -> None:
    """测试 404 异常处理。"""
    res = client.get("/not-found")
    assert res.status_code == 404
    data = res.json()
    assert data["code"] == 404


def test_route_not_found() -> None:
    """测试不存在的路由返回统一 404 响应。"""
    res = client.get("/no-such-route")
    assert res.status_code == 404
    assert res.json()["code"] == 404


def test_validation_error() -> None:
    """测试参数校验失败返回统一 422 响应。"""
    res = client.post("/validate", json={"item": "not-a-number"})
    assert res.status_code == 422
    data = res.json()
    assert data["code"] == 422
    assert data["message"] == "参数校验失败"
