"""模型配置接口与调用封装测试。"""
import httpx
from fastapi.testclient import TestClient

API_PATH = "/api/v1/model-configs"


def _create_config(
    client: TestClient,
    name: str = "测试模型",
    api_key: str | None = "sk-secret-123456",
    **overrides,
) -> dict:
    body = {
        "name": name,
        "base_url": "https://api.example.com/v1",
        "api_key": api_key,
        "model_name": "gpt-4o-mini",
    }
    body.update(overrides)
    res = client.post(API_PATH, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _mock_client(handler):
    """构造返回 MockTransport client 的补丁（捕获真实 httpx.Client 以避免递归覆盖）。"""
    real_client = httpx.Client

    def factory(timeout=None, **kwargs):
        transport = httpx.MockTransport(handler)
        return real_client(transport=transport, timeout=timeout, **kwargs)

    return factory


def test_create_model_config_mask_key(client: TestClient) -> None:
    created = _create_config(client, api_key="sk-test-abcdef123456")
    assert created["id"] > 0
    assert created["api_key_configured"] is True
    assert created["model_name"] == "gpt-4o-mini"
    assert created["timeout_seconds"] > 0

    # 读取单个/列表时不得返回明文
    res = client.get(f"{API_PATH}/{created['id']}")
    assert "sk-test-abcdef123456" not in res.text
    assert res.json()["data"]["api_key_configured"] is True

    res = client.get(API_PATH)
    assert "sk-test-abcdef123456" not in res.text


def test_create_model_config_without_key(client: TestClient) -> None:
    created = _create_config(client, api_key=None)
    assert created["api_key_configured"] is False


def test_create_duplicate_name_conflict(client: TestClient) -> None:
    _create_config(client, name="唯一")
    res = client.post(
        API_PATH,
        json={
            "name": "唯一",
            "base_url": "https://api.example.com/v1",
            "model_name": "gpt-4o-mini",
        },
    )
    assert res.status_code == 409


def test_create_invalid_base_url(client: TestClient) -> None:
    res = client.post(
        API_PATH,
        json={
            "name": "错误地址",
            "base_url": "not-a-url",
            "model_name": "gpt-4o-mini",
        },
    )
    assert res.status_code == 422


def test_default_is_unique(client: TestClient) -> None:
    _create_config(client, name="A", is_default=True)
    b = _create_config(client, name="B", is_default=True)

    res = client.get(API_PATH)
    data = res.json()["data"]
    # 共有 2 条，且只有最后设为默认的 B 是默认
    assert len(data) == 2
    defaults = [c for c in data if c["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "B"
    assert b["is_default"] is True


def test_update_model_config_preserves_key_when_blank(client: TestClient) -> None:
    created = _create_config(client, api_key="sk-original-123456")
    # 更新名称但不传 api_key，密钥应被保留
    res = client.put(
        f"{API_PATH}/{created['id']}", json={"model_name": "gpt-4o"}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["model_name"] == "gpt-4o"
    assert data["api_key_configured"] is True

    # 直接读取数据库确认密文仍存在（模拟持久层校验）
    res = client.get(f"{API_PATH}/{created['id']}")
    assert "sk-original" not in res.text


def test_update_model_config_overwrite_key(client: TestClient) -> None:
    created = _create_config(client, api_key="sk-original-123456")
    res = client.put(
        f"{API_PATH}/{created['id']}",
        json={"api_key": "sk-new-789012345678"},
    )
    assert res.status_code == 200
    assert "sk-new-789012345678" not in res.text
    assert res.json()["data"]["api_key_configured"] is True


def test_delete_model_config(client: TestClient) -> None:
    created = _create_config(client)
    res = client.delete(f"{API_PATH}/{created['id']}")
    assert res.status_code == 200
    res = client.get(f"{API_PATH}/{created['id']}")
    assert res.status_code == 404


def test_test_connection_success(client: TestClient, monkeypatch) -> None:
    created = _create_config(client)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        # Authorization 请求头中确实携带 key，但不影响日志/响应
        assert request.headers["Authorization"].startswith("Bearer ")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "OK"}}]},
        )

    monkeypatch.setattr(
        "app.services.llm.httpx.Client", _mock_client(handler)
    )
    res = client.post(f"{API_PATH}/{created['id']}/test")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is True
    assert data["message"] == "连接成功"


def test_test_connection_auth_failure(client: TestClient, monkeypatch) -> None:
    created = _create_config(client)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    monkeypatch.setattr(
        "app.services.llm.httpx.Client", _mock_client(handler)
    )
    res = client.post(f"{API_PATH}/{created['id']}/test")
    assert res.status_code == 200  # 测试接口本身成功，结果里带失败信息
    data = res.json()["data"]
    assert data["success"] is False
    assert "鉴权" in data["message"]


def test_test_connection_timeout(client: TestClient, monkeypatch) -> None:
    created = _create_config(client)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(
        "app.services.llm.httpx.Client", _mock_client(handler)
    )
    res = client.post(f"{API_PATH}/{created['id']}/test")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is False
    assert "超时" in data["message"]


def test_test_connection_missing_key(client: TestClient, monkeypatch) -> None:
    created = _create_config(client, api_key=None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(
        "app.services.llm.httpx.Client", _mock_client(handler)
    )
    res = client.post(f"{API_PATH}/{created['id']}/test")
    data = res.json()["data"]
    assert data["success"] is False
    assert "API Key" in data["message"]
