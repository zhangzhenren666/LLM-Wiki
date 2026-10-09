"""知识图谱 API 接口测试。"""
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


# ---------- 单页面图谱 ----------


def test_page_graph_with_relations(client: TestClient) -> None:
    """包含关系的页面应返回节点和边。"""
    kb = _create_kb(client)
    a = _create_page(client, kb["id"], "A")
    b = _create_page(client, kb["id"], "B")
    c = _create_page(client, kb["id"], "C")

    _create_relation(client, a["id"], b["id"], "related")
    _create_relation(client, c["id"], a["id"], "depends_on")

    res = client.get(f"/api/v1/graph/pages/{a['id']}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert len(data["nodes"]) == 3  # A, B, C
    assert len(data["edges"]) == 2

    node_ids = {n["id"] for n in data["nodes"]}
    assert a["id"] in node_ids
    assert b["id"] in node_ids
    assert c["id"] in node_ids


def test_page_graph_isolated(client: TestClient) -> None:
    """无关联关系的页面应只返回自身节点。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "孤立页面")

    res = client.get(f"/api/v1/graph/pages/{page['id']}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 0
    assert data["nodes"][0]["id"] == page["id"]


def test_page_graph_not_found(client: TestClient) -> None:
    """不存在的页面应返回 404。"""
    res = client.get("/api/v1/graph/pages/9999")
    assert res.status_code == 404


def test_page_graph_with_backlinks(client: TestClient) -> None:
    """内部链接（[[标题]]）产生的反向引用也应出现在图谱中。"""
    kb = _create_kb(client)
    target = _create_page(client, kb["id"], "目标页")
    _create_page(client, kb["id"], "源页", content="参见 [[目标页]]")

    res = client.get(f"/api/v1/graph/pages/{target['id']}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1  # link 类型边


def test_page_graph_edge_fields(client: TestClient) -> None:
    """边应包含 id, source, target, relation_type 等字段。"""
    kb = _create_kb(client)
    a = _create_page(client, kb["id"], "A")
    b = _create_page(client, kb["id"], "B")
    _create_relation(client, a["id"], b["id"], "parent")

    res = client.get(f"/api/v1/graph/pages/{a['id']}")
    data = res.json()["data"]
    edge = data["edges"][0]

    assert edge["id"] > 0
    assert edge["source"] == a["id"]
    assert edge["target"] == b["id"]
    assert "上级知识" in edge["relation_type"]


def test_page_graph_node_fields(client: TestClient) -> None:
    """节点应包含 id, label, title, slug, knowledge_base_id。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "节点测试")

    res = client.get(f"/api/v1/graph/pages/{page['id']}")
    data = res.json()["data"]
    node = data["nodes"][0]

    assert node["id"] == page["id"]
    assert node["label"] == "节点测试"
    assert node["title"] == "节点测试"
    assert node["slug"] != ""
    assert node["knowledge_base_id"] == kb["id"]


# ---------- 知识库整体图谱 ----------


def test_kb_graph_with_relations(client: TestClient) -> None:
    """知识库图谱应包含所有页面及其关系。"""
    kb = _create_kb(client)
    a = _create_page(client, kb["id"], "A")
    b = _create_page(client, kb["id"], "B")
    c = _create_page(client, kb["id"], "C")

    _create_relation(client, a["id"], b["id"], "related")
    _create_relation(client, b["id"], c["id"], "depends_on")

    res = client.get(f"/api/v1/graph/knowledge-bases/{kb['id']}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2


def test_kb_graph_empty(client: TestClient) -> None:
    """无页面的知识库应返回空图。"""
    kb = _create_kb(client)

    res = client.get(f"/api/v1/graph/knowledge-bases/{kb['id']}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["nodes"] == []
    assert data["edges"] == []


def test_kb_graph_not_found(client: TestClient) -> None:
    """不存在的知识库应返回 404。"""
    res = client.get("/api/v1/graph/knowledge-bases/9999")
    assert res.status_code == 404


def test_kb_graph_max_nodes(client: TestClient) -> None:
    """max_nodes 限制应生效。"""
    kb = _create_kb(client)
    for i in range(5):
        _create_page(client, kb["id"], f"页面{i}")

    res = client.get(
        f"/api/v1/graph/knowledge-bases/{kb['id']}?max_nodes=3"
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["nodes"]) == 3


def test_kb_graph_max_nodes_edges_filtered(client: TestClient) -> None:
    """max_nodes 限制时，超出节点的边应被过滤。"""
    kb = _create_kb(client)
    pages = [_create_page(client, kb["id"], f"P{i}") for i in range(4)]
    _create_relation(client, pages[0]["id"], pages[1]["id"])
    _create_relation(client, pages[2]["id"], pages[3]["id"])

    res = client.get(
        f"/api/v1/graph/knowledge-bases/{kb['id']}?max_nodes=2"
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["nodes"]) == 2

    node_ids = {n["id"] for n in data["nodes"]}
    for edge in data["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids