"""页面关系 CRUD 接口测试。"""
from fastapi.testclient import TestClient


def _create_kb(client: TestClient, name: str = "测试知识库") -> dict:
    res = client.post("/api/v1/knowledge-bases", json={"name": name})
    assert res.status_code == 200
    return res.json()["data"]


def _create_page(
    client: TestClient,
    kb_id: int,
    title: str = "测试页面",
    **overrides,
) -> dict:
    body = {"knowledge_base_id": kb_id, "title": title, **overrides}
    res = client.post("/api/v1/pages", json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _create_relation(
    client: TestClient,
    source_page_id: int,
    target_page_id: int,
    relation_type: str = "related",
) -> dict:
    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": source_page_id,
            "target_page_id": target_page_id,
            "relation_type": relation_type,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


# ---------- 创建关系 ----------


def test_create_relation_success(client: TestClient) -> None:
    """创建正常关系应成功。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源页面")
    tgt = _create_page(client, kb["id"], "目标页面")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": src["id"],
            "target_page_id": tgt["id"],
            "relation_type": "related",
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["source_page_id"] == src["id"]
    assert data["target_page_id"] == tgt["id"]
    assert data["relation_type"] == "related"
    assert data["source"] == "manual"
    assert data["knowledge_base_id"] == kb["id"]


def test_create_relation_all_types(client: TestClient) -> None:
    """所有关系类型（related, references, depends_on, parent）均可创建。"""
    kb = _create_kb(client)
    pages = [
        _create_page(client, kb["id"], f"页面{i}") for i in range(5)
    ]
    for i, rtype in enumerate(["related", "references", "depends_on", "parent"]):
        res = client.post(
            "/api/v1/relations",
            json={
                "source_page_id": pages[i]["id"],
                "target_page_id": pages[i + 1]["id"],
                "relation_type": rtype,
            },
        )
        assert res.status_code == 201, f"{rtype}: {res.text}"
        assert res.json()["data"]["relation_type"] == rtype


def test_create_relation_page_not_found(client: TestClient) -> None:
    """源或目标页面不存在时应返回 404。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "存在的页面")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": page["id"],
            "target_page_id": 9999,
            "relation_type": "related",
        },
    )
    assert res.status_code == 404

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": 9999,
            "target_page_id": page["id"],
            "relation_type": "related",
        },
    )
    assert res.status_code == 404


def test_create_relation_self_reference(client: TestClient) -> None:
    """不能与自身建立关系。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "自引用测试")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": page["id"],
            "target_page_id": page["id"],
            "relation_type": "related",
        },
    )
    assert res.status_code == 400


def test_create_relation_cross_kb(client: TestClient) -> None:
    """不能跨知识库建立关系。"""
    kb1 = _create_kb(client, "知识库1")
    kb2 = _create_kb(client, "知识库2")
    src = _create_page(client, kb1["id"], "KB1 页面")
    tgt = _create_page(client, kb2["id"], "KB2 页面")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": src["id"],
            "target_page_id": tgt["id"],
            "relation_type": "related",
        },
    )
    assert res.status_code == 400


def test_create_relation_duplicate(client: TestClient) -> None:
    """同类型重复关系应返回 409。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")

    _create_relation(client, src["id"], tgt["id"], "related")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": src["id"],
            "target_page_id": tgt["id"],
            "relation_type": "related",
        },
    )
    assert res.status_code == 409


def test_create_relation_different_types_allowed(client: TestClient) -> None:
    """相同源/目标但不同关系类型，允许共存。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")

    rel1 = _create_relation(client, src["id"], tgt["id"], "related")
    rel2 = _create_relation(client, src["id"], tgt["id"], "references")

    assert rel1["id"] != rel2["id"]


def test_create_relation_invalid_type(client: TestClient) -> None:
    """无效的关系类型应返回 422。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")

    res = client.post(
        "/api/v1/relations",
        json={
            "source_page_id": src["id"],
            "target_page_id": tgt["id"],
            "relation_type": "invalid_type",
        },
    )
    assert res.status_code == 422


# ---------- 删除关系 ----------


def test_delete_relation(client: TestClient) -> None:
    """删除已存在的关系。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")
    rel = _create_relation(client, src["id"], tgt["id"])

    res = client.delete(f"/api/v1/relations/{rel['id']}")
    assert res.status_code == 200

    # 确认已删除
    res2 = client.get(f"/api/v1/relations?page_id={src['id']}")
    assert res2.status_code == 200
    assert len(res2.json()["data"]) == 0


def test_delete_relation_not_found(client: TestClient) -> None:
    """删除不存在的关系应返回 404。"""
    res = client.delete("/api/v1/relations/9999")
    assert res.status_code == 404


def test_delete_relation_cascade_on_page_delete(client: TestClient) -> None:
    """删除页面时关联关系自动清理。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")
    _create_relation(client, src["id"], tgt["id"])

    # 删除源页面
    client.delete(f"/api/v1/pages/{src['id']}")

    # 确认关系被级联删除
    res = client.get(f"/api/v1/relations?page_id={tgt['id']}")
    assert len(res.json()["data"]) == 0


# ---------- 查询关系 ----------


def test_list_relations_all(client: TestClient) -> None:
    """查询全部关系（无筛选）。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt = _create_page(client, kb["id"], "目标")
    _create_relation(client, src["id"], tgt["id"])

    res = client.get("/api/v1/relations")
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1


def test_list_relations_by_kb(client: TestClient) -> None:
    """按知识库筛选关系。"""
    kb1 = _create_kb(client, "KB1")
    kb2 = _create_kb(client, "KB2")
    p1 = _create_page(client, kb1["id"], "P1")
    p2 = _create_page(client, kb1["id"], "P2")
    p3 = _create_page(client, kb2["id"], "P3")
    p4 = _create_page(client, kb2["id"], "P4")

    _create_relation(client, p1["id"], p2["id"])
    _create_relation(client, p3["id"], p4["id"])

    res = client.get(f"/api/v1/relations?knowledge_base_id={kb1['id']}")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


def test_list_relations_by_type(client: TestClient) -> None:
    """按类型筛选关系。"""
    kb = _create_kb(client)
    src = _create_page(client, kb["id"], "源")
    tgt1 = _create_page(client, kb["id"], "目标1")
    tgt2 = _create_page(client, kb["id"], "目标2")

    _create_relation(client, src["id"], tgt1["id"], "related")
    _create_relation(client, src["id"], tgt2["id"], "depends_on")

    res = client.get("/api/v1/relations?relation_type=related")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["relation_type"] == "related"


def test_list_relations_by_page(client: TestClient) -> None:
    """按页面筛选（同时匹配源和目标）。"""
    kb = _create_kb(client)
    a = _create_page(client, kb["id"], "A")
    b = _create_page(client, kb["id"], "B")
    c = _create_page(client, kb["id"], "C")

    _create_relation(client, a["id"], b["id"], "related")
    _create_relation(client, c["id"], a["id"], "depends_on")

    # 查询 A 的关系（出向 + 入向）
    res = client.get(f"/api/v1/relations?page_id={a['id']}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2  # A -> B 和 C -> A


# ---------- 查询页面关系（入向+出向） ----------


def test_get_page_relations_both_directions(client: TestClient) -> None:
    """GET /pages/{id}/relations 应同时返回出向和入向。"""
    kb = _create_kb(client)
    a = _create_page(client, kb["id"], "A")
    b = _create_page(client, kb["id"], "B")
    c = _create_page(client, kb["id"], "C")

    _create_relation(client, a["id"], b["id"], "related")  # A -> B
    _create_relation(client, c["id"], a["id"], "depends_on")  # C -> A

    res = client.get(f"/api/v1/pages/{a['id']}/relations")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["outgoing"]) == 1  # A -> B
    assert len(data["incoming"]) == 1  # C -> A
    assert data["outgoing"][0]["related_page"]["title"] == "B"
    assert data["incoming"][0]["related_page"]["title"] == "C"


def test_get_page_relations_empty(client: TestClient) -> None:
    """无关系的页面应返回空列表。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "孤立页面")

    res = client.get(f"/api/v1/pages/{page['id']}/relations")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["outgoing"] == []
    assert data["incoming"] == []


def test_get_page_relations_not_found(client: TestClient) -> None:
    """查询不存在页面的关系应返回 404。"""
    res = client.get("/api/v1/pages/9999/relations")
    assert res.status_code == 404