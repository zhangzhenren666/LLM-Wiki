"""搜索功能 API 测试。"""
from fastapi.testclient import TestClient


def _create_kb(client: TestClient, name: str = "搜索测试库") -> dict:
    res = client.post("/api/v1/knowledge-bases", json={"name": name})
    assert res.status_code == 200
    return res.json()["data"]


def _create_page(client: TestClient, kb_id: int, title: str, content: str = "", tags: list[str] | None = None) -> dict:
    """创建页面，并可选择添加标签。"""
    res = client.post(
        "/api/v1/pages",
        json={
            "knowledge_base_id": kb_id,
            "title": title,
            "content": content,
        },
    )
    assert res.status_code == 200
    page = res.json()["data"]
    if tags:
        client.post(f"/api/v1/pages/{page['id']}/tags", json={"tags": tags})
    return page


# ---------- 标题搜索 ----------


def test_search_by_title(client: TestClient) -> None:
    """搜索标题关键词应返回匹配页面。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "Python 入门指南", "这是一篇教程。")
    _create_page(client, kb["id"], "SQL 教程", "数据库相关。")

    res = client.get("/api/v1/search", params={"q": "Python"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    titles = [item["title"] for item in data["items"]]
    assert "Python 入门指南" in titles
    assert data["items"][0]["match_type"] == "title"


def test_search_case_insensitive(client: TestClient) -> None:
    """搜索应不区分大小写。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "Python Programming", "content here")

    res = client.get("/api/v1/search", params={"q": "python"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["title"] == "Python Programming"


# ---------- 内容搜索 ----------


def test_search_by_content(client: TestClient) -> None:
    """搜索正文内容应返回匹配页面。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "笔记", "这个项目使用 FastAPI 框架构建后端 API。")

    res = client.get("/api/v1/search", params={"q": "FastAPI"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["match_type"] == "content"
    # 应有片段
    assert data["items"][0]["snippet"] is not None


def test_search_content_snippet(client: TestClient) -> None:
    """内容匹配应返回包含关键词高亮的摘要片段。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "设计文档", "架构设计采用了微服务与事件驱动相结合的方式，保证了系统的高可用性和可扩展性。")

    res = client.get("/api/v1/search", params={"q": "事件驱动"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    snippet = data["items"][0]["snippet"]
    assert snippet is not None
    assert "**事件驱动**" in snippet


# ---------- 标签搜索 ----------


def test_search_by_tag(client: TestClient) -> None:
    """搜索标签名应返回包含该标签的页面。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "Django 教程", "Django 入门", tags=["python", "web"])
    _create_page(client, kb["id"], "Spring Boot", "Java 框架", tags=["java", "web"])

    res = client.get("/api/v1/search", params={"q": "python"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    # 应包含标签匹配的页面
    titles = [item["title"] for item in data["items"]]
    assert "Django 教程" in titles


def test_search_tag_partial_match(client: TestClient) -> None:
    """标签部分匹配也应返回。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "某页面", "内容", tags=["machine-learning"])

    res = client.get("/api/v1/search", params={"q": "machine"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1


# ---------- 空关键词 ----------


def test_search_empty_query(client: TestClient) -> None:
    """空关键词应返回 422 校验错误。"""
    res = client.get("/api/v1/search", params={"q": ""})
    assert res.status_code == 422


# ---------- 知识库过滤 ----------


def test_search_filter_by_kb(client: TestClient) -> None:
    """限定知识库 ID 只返回该知识库的匹配。"""
    kb1 = _create_kb(client, "KB1")
    kb2 = _create_kb(client, "KB2")
    _create_page(client, kb1["id"], "Alpha 页面", "alpha content")
    _create_page(client, kb2["id"], "Beta Alpha", "beta content")

    res = client.get("/api/v1/search", params={"q": "Alpha", "knowledge_base_id": kb1["id"]})
    assert res.status_code == 200
    data = res.json()["data"]
    for item in data["items"]:
        assert item["knowledge_base_id"] == kb1["id"]


# ---------- 分页 ----------


def test_search_pagination(client: TestClient) -> None:
    """分页参数应正常工作。"""
    kb = _create_kb(client)
    for i in range(5):
        _create_page(client, kb["id"], f"搜索测试页面 {i}", f"内容 {i}")

    res = client.get("/api/v1/search", params={"q": "搜索测试", "page": 1, "page_size": 2})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] >= 5


# ---------- 无结果 ----------


def test_search_no_results(client: TestClient) -> None:
    """无匹配时应返回空列表。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "Hello", "world")

    res = client.get("/api/v1/search", params={"q": "不存在的关键词xyz"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 0
    assert len(data["items"]) == 0


# ---------- 特殊字符 ----------


def test_search_special_chars(client: TestClient) -> None:
    """SQL 特殊字符查询应安全处理。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "SQL 注入测试 % _", "SELECT * FROM users")

    res = client.get("/api/v1/search", params={"q": "%"})
    assert res.status_code == 200
    # 不应崩溃，即使无匹配也正常返回
    data = res.json()["data"]
    assert data is not None


def test_search_with_percent(client: TestClient) -> None:
    """% 通配符作为关键词应正常搜索。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "100% 完成", "百分号测试")

    res = client.get("/api/v1/search", params={"q": "100%"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1


# ---------- 匹配类型优先级 ----------


def test_search_match_type_priority(client: TestClient) -> None:
    """同时匹配标题和内容时应优先返回 title。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "React 框架简介", "React 是一个流行的前端框架。")

    res = client.get("/api/v1/search", params={"q": "React"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["match_type"] == "title"


def test_search_multiple_fields(client: TestClient) -> None:
    """跨字段搜索应去重（同一页面不会出现多次）。"""
    kb = _create_kb(client)
    _create_page(client, kb["id"], "Docker 指南", "Docker 容器化部署教程", tags=["docker"])

    res = client.get("/api/v1/search", params={"q": "Docker"})
    assert res.status_code == 200
    data = res.json()["data"]
    # 同一页面只应出现一次
    page_ids = [item["page_id"] for item in data["items"]]
    assert len(page_ids) == len(set(page_ids))