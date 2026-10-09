"""Wiki 页面 CRUD 接口测试。"""
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


# ---------- 创建 ----------


def test_create_page(client: TestClient) -> None:
    kb = _create_kb(client)
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": kb["id"], "title": "首页"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["title"] == "首页"
    assert data["slug"]  # 自动生成
    assert data["content"] == ""
    assert data["status"] == "draft"
    assert data["parent_id"] is None
    assert data["knowledge_base_id"] == kb["id"]


def test_create_page_kb_not_found(client: TestClient) -> None:
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": 9999, "title": "孤儿页面"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == 404


def test_create_page_empty_title(client: TestClient) -> None:
    kb = _create_kb(client)
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": kb["id"], "title": "   "},
    )
    assert res.status_code == 422


def test_create_page_explicit_slug_conflict(client: TestClient) -> None:
    kb = _create_kb(client)
    _create_page(client, kb["id"], "页面A", slug="my-http-page")
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": kb["id"], "title": "页面B", "slug": "my-http-page"},
    )
    assert res.status_code == 409
    assert res.json()["code"] == 409


def test_create_page_auto_unique_slug(client: TestClient) -> None:
    """自动生成的 slug 冲突时自动加后缀去重。"""
    kb = _create_kb(client)
    first = _create_page(client, kb["id"], "重复标题")
    second = _create_page(client, kb["id"], "重复标题")
    assert first["slug"] == "重复标题"
    assert second["slug"] == "重复标题-2"
    assert second["slug"] != first["slug"]


def test_create_page_parent_valid(client: TestClient) -> None:
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父页面")
    child = _create_page(client, kb["id"], "子页面", parent_id=parent["id"])
    assert child["parent_id"] == parent["id"]


def test_create_page_parent_not_found(client: TestClient) -> None:
    kb = _create_kb(client)
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": kb["id"], "title": "子页面", "parent_id": 9999},
    )
    assert res.status_code == 404


def test_create_page_parent_diff_kb(client: TestClient) -> None:
    """父页面必须属于同一知识库，否则 400。"""
    kb1 = _create_kb(client, "知识库1")
    kb2 = _create_kb(client, "知识库2")
    parent = _create_page(client, kb1["id"], "父页面")
    res = client.post(
        "/api/v1/pages",
        json={"knowledge_base_id": kb2["id"], "title": "子页面", "parent_id": parent["id"]},
    )
    assert res.status_code == 400


# ---------- 列表 ----------


def test_list_pages_filter_by_kb(client: TestClient) -> None:
    kb1 = _create_kb(client, "知识库1")
    kb2 = _create_kb(client, "知识库2")
    _create_page(client, kb1["id"], "页面1")
    _create_page(client, kb2["id"], "页面2")

    res = client.get(f"/api/v1/pages?knowledge_base_id={kb1['id']}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "页面1"


def test_list_pages_top_level(client: TestClient) -> None:
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "顶层")
    _create_page(client, kb["id"], "子页面", parent_id=parent["id"])

    # parent_id=0 仅返回顶层
    res = client.get(f"/api/v1/pages?knowledge_base_id={kb['id']}&parent_id=0")
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "顶层"

    # 按父页面过滤
    res = client.get(f"/api/v1/pages?knowledge_base_id={kb['id']}&parent_id={parent['id']}")
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "子页面"


def test_list_pages_status_filter(client: TestClient) -> None:
    kb = _create_kb(client)
    _create_page(client, kb["id"], "草稿页")
    _create_page(client, kb["id"], "发布页", status="published")

    res = client.get(f"/api/v1/pages?knowledge_base_id={kb['id']}&status=published")
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "发布页"


def test_list_pages_keyword(client: TestClient) -> None:
    kb = _create_kb(client)
    _create_page(client, kb["id"], "关于我们")
    _create_page(client, kb["id"], "使用手册")

    res = client.get(f"/api/v1/pages?knowledge_base_id={kb['id']}&keyword=手册")
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "使用手册"


# ---------- 读取 ----------


def test_get_page(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "详情页")
    res = client.get(f"/api/v1/pages/{page['id']}")
    assert res.status_code == 200
    assert res.json()["data"]["title"] == "详情页"


def test_get_page_not_found(client: TestClient) -> None:
    res = client.get("/api/v1/pages/9999")
    assert res.status_code == 404
    assert res.json()["code"] == 404


# ---------- 更新 ----------


def test_update_page_fields(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "旧标题")
    res = client.put(
        f"/api/v1/pages/{page['id']}",
        json={"title": "新标题", "status": "published"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["title"] == "新标题"
    assert data["status"] == "published"


def test_update_page_slug_conflict(client: TestClient) -> None:
    kb = _create_kb(client)
    page_a = _create_page(client, kb["id"], "页面A")
    page_b = _create_page(client, kb["id"], "页面B", slug="page-b")
    res = client.put(
        f"/api/v1/pages/{page_a['id']}",
        json={"slug": "page-b"},
    )
    assert res.status_code == 409


def test_update_page_parent_cycle(client: TestClient) -> None:
    """不能将页面设置为自身的父/后代，否则 400。"""
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父")
    child = _create_page(client, kb["id"], "子", parent_id=parent["id"])

    # 将父页面挂到子页面下 → 环
    res = client.put(
        f"/api/v1/pages/{parent['id']}",
        json={"parent_id": child["id"]},
    )
    assert res.status_code == 400

    # 将页面挂到自身下 → 环
    res = client.put(
        f"/api/v1/pages/{child['id']}",
        json={"parent_id": child["id"]},
    )
    assert res.status_code == 400


def test_update_page_set_parent_to_top(client: TestClient) -> None:
    """显式传 parent_id=null 时置为顶层。"""
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父")
    child = _create_page(client, kb["id"], "子", parent_id=parent["id"])
    assert child["parent_id"] == parent["id"]

    res = client.put(f"/api/v1/pages/{child['id']}", json={"parent_id": None})
    assert res.status_code == 200
    assert res.json()["data"]["parent_id"] is None


def test_update_page_content_null(client: TestClient) -> None:
    """更新时传 content=null 应被置为空字符串而非报错。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "页面", content="原始内容")
    res = client.put(f"/api/v1/pages/{page['id']}", json={"content": None})
    assert res.status_code == 200
    assert res.json()["data"]["content"] == ""


def test_update_page_not_found(client: TestClient) -> None:
    res = client.put("/api/v1/pages/9999", json={"title": "不存在"})
    assert res.status_code == 404


# ---------- 删除 ----------


def test_delete_page(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "待删除")
    res = client.delete(f"/api/v1/pages/{page['id']}")
    assert res.status_code == 200
    assert res.json()["message"] == "删除成功"

    res = client.get(f"/api/v1/pages/{page['id']}")
    assert res.status_code == 404


def test_delete_page_not_found(client: TestClient) -> None:
    res = client.delete("/api/v1/pages/9999")
    assert res.status_code == 404


# ---------- 标签 ----------


def test_add_tags_to_page(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "带标签页面")
    res = client.post(
        f"/api/v1/pages/{page['id']}/tags",
        json={"tags": ["前端", "React"]},
    )
    assert res.status_code == 200
    assert set(res.json()["data"]["tags"]) == {"前端", "React"}


def test_add_tags_dedupe_case_insensitive(client: TestClient) -> None:
    """重复标签（含大小写变体）自动去重。"""
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "去重页面")
    res = client.post(
        f"/api/v1/pages/{page['id']}/tags",
        json={"tags": ["React", "react", "REACT", "前端"]},
    )
    assert res.status_code == 200
    # 大小写不敏感去重后应仅剩 2 个
    tags = res.json()["data"]["tags"]
    assert len(tags) == 2
    assert set(t.lower() for t in tags) == {"react", "前端"}


def test_add_tags_to_page_not_found(client: TestClient) -> None:
    res = client.post(
        "/api/v1/pages/9999/tags",
        json={"tags": ["前端"]},
    )
    assert res.status_code == 404


def test_add_tags_empty_list(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "页面")
    res = client.post(f"/api/v1/pages/{page['id']}/tags", json={"tags": []})
    assert res.status_code == 422


def test_remove_tags_from_page(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "移除标签页面")
    client.post(
        f"/api/v1/pages/{page['id']}/tags",
        json={"tags": ["前端", "React"]},
    )
    res = client.delete(
        f"/api/v1/pages/{page['id']}/tags",
        params={"tags": ["React"]},
    )
    assert res.status_code == 200
    assert res.json()["data"]["tags"] == ["前端"]


def test_list_pages_filter_by_tag(client: TestClient) -> None:
    kb = _create_kb(client)
    page_a = _create_page(client, kb["id"], "带标签A")
    _create_page(client, kb["id"], "无标签页面")
    client.post(f"/api/v1/pages/{page_a['id']}/tags", json={"tags": ["热门"]})

    res = client.get(f"/api/v1/pages?knowledge_base_id={kb['id']}&tag=热门")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "带标签A"


def test_list_knowledge_base_tags(client: TestClient) -> None:
    kb1 = _create_kb(client, "知识库1")
    kb2 = _create_kb(client, "知识库2")
    p1 = _create_page(client, kb1["id"], "页面1")
    p2 = _create_page(client, kb1["id"], "页面2")
    client.post(f"/api/v1/pages/{p1['id']}/tags", json={"tags": ["前端"]})
    client.post(f"/api/v1/pages/{p2['id']}/tags", json={"tags": ["前端", "后端"]})
    _create_page(client, kb2["id"], "另一个库")

    # kb1 的标签按名称排序去重
    res = client.get(f"/api/v1/knowledge-bases/{kb1['id']}/tags")
    assert res.status_code == 200
    assert res.json()["data"] == ["前端", "后端"]

    # 跨库隔离
    res = client.get(f"/api/v1/knowledge-bases/{kb2['id']}/tags")
    assert res.status_code == 200
    assert res.json()["data"] == []


# ---------- 移动（调整目录层级） ----------


def test_move_page_to_parent(client: TestClient) -> None:
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "新父页面")
    page = _create_page(client, kb["id"], "要移动的页面")
    res = client.put(
        f"/api/v1/pages/{page['id']}/move",
        json={"parent_id": parent["id"]},
    )
    assert res.status_code == 200
    assert res.json()["data"]["parent_id"] == parent["id"]


def test_move_page_to_top(client: TestClient) -> None:
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父页面")
    child = _create_page(client, kb["id"], "子页面", parent_id=parent["id"])
    assert child["parent_id"] == parent["id"]

    res = client.put(f"/api/v1/pages/{child['id']}/move", json={"parent_id": None})
    assert res.status_code == 200
    assert res.json()["data"]["parent_id"] is None


def test_move_page_cycle(client: TestClient) -> None:
    """移动到自身的后代会发生循环，应 400。"""
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父")
    child = _create_page(client, kb["id"], "子", parent_id=parent["id"])

    # 将父移动到子下 → 环
    res = client.put(
        f"/api/v1/pages/{parent['id']}/move",
        json={"parent_id": child["id"]},
    )
    assert res.status_code == 400


def test_move_page_parent_not_found(client: TestClient) -> None:
    kb = _create_kb(client)
    page = _create_page(client, kb["id"], "页面")
    res = client.put(
        f"/api/v1/pages/{page['id']}/move",
        json={"parent_id": 9999},
    )
    assert res.status_code == 404


def test_move_page_preserves_content(client: TestClient) -> None:
    """移动不影响页面内容与其他属性。"""
    kb = _create_kb(client)
    parent = _create_page(client, kb["id"], "父页面")
    page = _create_page(client, kb["id"], "内容", content="# 标题\n正文")
    client.post(f"/api/v1/pages/{page['id']}/tags", json={"tags": ["前端"]})

    res = client.put(
        f"/api/v1/pages/{page['id']}/move",
        json={"parent_id": parent["id"]},
    )
    data = res.json()["data"]
    assert data["content"] == "# 标题\n正文"
    assert data["parent_id"] == parent["id"]
    assert data["tags"] == ["前端"]


# ---------- 内部链接 / 反向引用 ----------


def test_backlinks_recognized_on_create(client: TestClient) -> None:
    """页面正文含 [[标题]] 时，自动识别并对目标页面生成反向引用。"""
    kb = _create_kb(client)
    target = _create_page(client, kb["id"], "目标页面")
    source = _create_page(
        client,
        kb["id"],
        "来源页面",
        content="参见 [[目标页面]] 了解更多。",
    )
    assert source["id"] != target["id"]

    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "来源页面"
    assert data[0]["source"] == "backlink"


def test_backlinks_ambiguous_title_not_linked(client: TestClient) -> None:
    """同名页面存在（歧义）时不建立反向引用，避免错误跳转。"""
    kb = _create_kb(client)
    # 两个同名页面
    _create_page(client, kb["id"], "同名页")
    _create_page(client, kb["id"], "同名页")
    source = _create_page(client, kb["id"], "来源", content="引用 [[同名页]]")

    # 歧义不产生反向引用
    res = client.get(f"/api/v1/pages/{source['id']}/backlinks")
    assert res.json()["data"] == []


def test_backlinks_missing_title_not_linked(client: TestClient) -> None:
    """引用的页面标题不存在时不建立反向引用。"""
    kb = _create_kb(client)
    source = _create_page(client, kb["id"], "来源", content="引用 [[不存在的页面]]")
    res = client.get(f"/api/v1/pages/{source['id']}/backlinks")
    assert res.json()["data"] == []


def test_backlinks_only_exact_title_in_same_kb(client: TestClient) -> None:
    """精确标题且同在目标知识库内才建立关系，跨库同名不建立。"""
    kb1 = _create_kb(client, "知识库1")
    kb2 = _create_kb(client, "知识库2")
    target1 = _create_page(client, kb1["id"], "同名标题")
    target2 = _create_page(client, kb2["id"], "同名标题")
    source = _create_page(client, kb1["id"], "来源", content="链接到 [[同名标题]]")

    # kb2 中的同名页面不应被 kb1 的来源页面引用到
    res = client.get(f"/api/v1/pages/{target2['id']}/backlinks")
    assert res.json()["data"] == []
    # kb1 中的目标页面应被正确引用
    res = client.get(f"/api/v1/pages/{target1['id']}/backlinks")
    assert len(res.json()["data"]) == 1


def test_backlinks_multi_targets(client: TestClient) -> None:
    """一个来源页面可引用多个目标页面。"""
    kb = _create_kb(client)
    t1 = _create_page(client, kb["id"], "甲")
    t2 = _create_page(client, kb["id"], "乙")
    _create_page(
        client,
        kb["id"],
        "来源",
        content="看 [[甲]] 和 [[乙]] 和 [[甲]]",
    )
    res = client.get(f"/api/v1/pages/{t1['id']}/backlinks")
    assert len(res.json()["data"]) == 1
    res = client.get(f"/api/v1/pages/{t2['id']}/backlinks")
    assert len(res.json()["data"]) == 1


def test_backlinks_sync_after_content_update(client: TestClient) -> None:
    """内容更新后反向链接关系被重建。"""
    kb = _create_kb(client)
    target = _create_page(client, kb["id"], "目标页面")
    source = _create_page(client, kb["id"], "来源", content="无链接")

    # 初始无反向引用
    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert res.json()["data"] == []

    # 更新内容加入链接
    client.put(
        f"/api/v1/pages/{source['id']}",
        json={"content": "现在引用 [[目标页面]]"},
    )
    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert len(res.json()["data"]) == 1

    # 移除链接后关系消失
    client.put(f"/api/v1/pages/{source['id']}", json={"content": "不再引用"})
    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert res.json()["data"] == []


def test_backlinks_page_not_found(client: TestClient) -> None:
    """查询不存在页面的反向引用应 404。"""
    res = client.get("/api/v1/pages/9999/backlinks")
    assert res.status_code == 404
    assert res.json()["code"] == 404


def test_backlinks_cascade_on_delete(client: TestClient) -> None:
    """删除来源页面后，不产生对目标页面的无效反向引用。"""
    kb = _create_kb(client)
    target = _create_page(client, kb["id"], "目标页面")
    source = _create_page(client, kb["id"], "来源", content="引用 [[目标页面]]")

    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert len(res.json()["data"]) == 1

    # 删除来源页面
    client.delete(f"/api/v1/pages/{source['id']}")

    res = client.get(f"/api/v1/pages/{target['id']}/backlinks")
    assert res.json()["data"] == []
