"""知识库 CRUD 接口测试。"""
from fastapi.testclient import TestClient


def _create_kb(client: TestClient, name: str, description: str | None = None) -> dict:
    body = {"name": name}
    if description is not None:
        body["description"] = description
    res = client.post("/api/v1/knowledge-bases", json=body)
    assert res.status_code == 200
    return res.json()["data"]


def test_create_knowledge_base(client: TestClient) -> None:
    res = client.post(
        "/api/v1/knowledge-bases",
        json={"name": "研发知识库", "description": "研发相关"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "研发知识库"
    assert data["data"]["description"] == "研发相关"
    assert data["data"]["id"] > 0
    assert data["data"]["created_at"] is not None


def test_create_knowledge_base_empty_name(client: TestClient) -> None:
    res = client.post("/api/v1/knowledge-bases", json={"name": "   "})
    assert res.status_code == 422
    assert res.json()["code"] == 422


def test_create_duplicate_name_conflict(client: TestClient) -> None:
    _create_kb(client, "重复知识库")
    res = client.post("/api/v1/knowledge-bases", json={"name": "重复知识库"})
    assert res.status_code == 409
    assert res.json()["code"] == 409


def test_list_knowledge_bases(client: TestClient) -> None:
    _create_kb(client, "知识库A")
    _create_kb(client, "知识库B")
    res = client.get("/api/v1/knowledge-bases")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 0
    assert len(data["data"]) == 2


def test_get_knowledge_base(client: TestClient) -> None:
    created = _create_kb(client, "单个知识库", "描述")
    res = client.get(f"/api/v1/knowledge-bases/{created['id']}")
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "单个知识库"


def test_get_knowledge_base_not_found(client: TestClient) -> None:
    res = client.get("/api/v1/knowledge-bases/9999")
    assert res.status_code == 404
    assert res.json()["code"] == 404


def test_update_knowledge_base(client: TestClient) -> None:
    created = _create_kb(client, "旧名称")
    res = client.put(
        f"/api/v1/knowledge-bases/{created['id']}",
        json={"name": "新名称", "description": "新描述"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "新名称"
    assert data["description"] == "新描述"


def test_update_knowledge_base_not_found(client: TestClient) -> None:
    res = client.put(
        "/api/v1/knowledge-bases/9999",
        json={"name": "不存在"},
    )
    assert res.status_code == 404


def test_update_duplicate_name_conflict(client: TestClient) -> None:
    _create_kb(client, "已有")
    created = _create_kb(client, "待改")
    res = client.put(
        f"/api/v1/knowledge-bases/{created['id']}",
        json={"name": "已有"},
    )
    assert res.status_code == 409


def test_delete_knowledge_base(client: TestClient) -> None:
    created = _create_kb(client, "待删除")
    res = client.delete(f"/api/v1/knowledge-bases/{created['id']}")
    assert res.status_code == 200
    assert res.json()["message"] == "删除成功"

    # 删除后查询应 404
    res = client.get(f"/api/v1/knowledge-bases/{created['id']}")
    assert res.status_code == 404


def test_delete_knowledge_base_not_found(client: TestClient) -> None:
    res = client.delete("/api/v1/knowledge-bases/9999")
    assert res.status_code == 404
