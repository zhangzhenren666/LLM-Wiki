"""文档处理任务功能测试。

后台 worker 在测试中默认关闭，任务由测试直接调用 service（模拟后台执行）流转。
"""
import io
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.models import DocumentTask, TaskStatus
from app.services.document_task import DocumentTaskService


def _upload(client: TestClient, kb_id: int, request_id: str | None = None,
            name: str | None = None) -> dict:
    content = "# 标题\n\n正文。"
    filename = name or "task-test.md"
    res = client.post(
        "/api/v1/documents/upload",
        data={
            "knowledge_base_id": kb_id,
            "request_id": request_id or "",
        },
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/markdown")},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _create_kb(client: TestClient, name: str = "任务知识库") -> dict:
    res = client.post("/api/v1/knowledge-bases", json={"name": name})
    assert res.status_code == 200
    return res.json()["data"]


def _latest_task(client: TestClient) -> dict:
    res = client.get("/api/v1/document-tasks")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    return data[0]


# ---------- 上传后自动创建任务 ----------


def test_upload_creates_pending_task(client: TestClient) -> None:
    kb = _create_kb(client)
    doc = _upload(client, kb["id"])

    res = client.get("/api/v1/document-tasks")
    assert res.status_code == 200
    tasks = res.json()["data"]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "pending"
    assert task["document_id"] == doc["id"]
    assert task["knowledge_base_id"] == kb["id"]
    assert task["attempts"] == 0


def test_list_filter_by_status(client: TestClient) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    _upload(client, kb["id"], name="second.md")

    # 全部 → 2
    res = client.get("/api/v1/document-tasks")
    assert len(res.json()["data"]) == 2

    # 过滤 pending → 2
    res = client.get("/api/v1/document-tasks", params={"status": "pending"})
    assert len(res.json()["data"]) == 2

    # 过滤 completed → 0
    res = client.get("/api/v1/document-tasks", params={"status": "completed"})
    assert len(res.json()["data"]) == 0


def test_list_filter_by_kb(client: TestClient) -> None:
    kb1 = _create_kb(client, "KB1")
    kb2 = _create_kb(client, "KB2")
    _upload(client, kb1["id"])
    _upload(client, kb2["id"])

    res = client.get(
        "/api/v1/document-tasks", params={"knowledge_base_id": kb1["id"]}
    )
    tasks = res.json()["data"]
    assert len(tasks) == 1
    assert tasks[0]["knowledge_base_id"] == kb1["id"]


# ---------- 任务详情与处理记录 ----------


def test_task_detail_contains_steps_after_process(
    client: TestClient, db_session
) -> None:
    kb = _create_kb(client)
    doc = _upload(client, kb["id"])
    task = _latest_task(client)
    task_id = task["id"]

    # 模拟后台执行
    service = DocumentTaskService(db_session)
    result = service.process_task(task_id)
    assert result.status == TaskStatus.COMPLETED
    assert result.progress == 100

    # 详情含处理记录步骤
    res = client.get(f"/api/v1/document-tasks/{task_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "completed"
    assert data["attempts"] == 1
    assert data["started_at"] is not None
    assert data["finished_at"] is not None
    assert len(data["steps"]) == 3
    step_parse = data["steps"][0]
    assert step_parse["step_name"] == "解析文档"
    assert step_parse["status"] == "completed"
    assert step_parse["page_id"] == doc["page_id"]
    step_ai = data["steps"][1]
    assert step_ai["step_name"] == "AI知识提取"
    assert step_ai["status"] == "completed"
    step_rel = data["steps"][2]
    assert step_rel["step_name"] == "关系构建"
    assert step_rel["status"] == "completed"


def test_task_detail_not_found(client: TestClient) -> None:
    res = client.get("/api/v1/document-tasks/9999")
    assert res.status_code == 404


# ---------- 失败与重试 ----------


def test_retry_failed_task(client: TestClient, db_session) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    task = _latest_task(client)
    task_id = task["id"]

    # 手动置为失败
    t = db_session.get(DocumentTask, task_id)
    t.status = TaskStatus.FAILED
    t.error_message = "模拟失败原因"
    db_session.commit()

    res = client.post(f"/api/v1/document-tasks/{task_id}/retry")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "pending"
    assert data["error_message"] is None


def test_retry_completed_rejected(client: TestClient, db_session) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    task_id = _latest_task(client)["id"]

    DocumentTaskService(db_session).process_task(task_id)

    res = client.post(f"/api/v1/document-tasks/{task_id}/retry")
    assert res.status_code == 409


def test_retry_after_max_attempts(client: TestClient, db_session) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    task_id = _latest_task(client)["id"]

    # 已达最大执行次数
    t = db_session.get(DocumentTask, task_id)
    t.status = TaskStatus.FAILED
    t.attempts = t.max_attempts  # attempts >= max
    db_session.commit()

    result = DocumentTaskService(db_session).process_task(task_id)
    assert result.status == TaskStatus.FAILED
    assert "最大" in (result.error_message or "")


# ---------- 中断恢复 ----------


def test_recover_interrupted(client: TestClient, db_session) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    task_id = _latest_task(client)["id"]

    # 模拟：任务卡在 processing 且开始于很久以前
    t = db_session.get(DocumentTask, task_id)
    t.status = TaskStatus.PROCESSING
    t.started_at = datetime.now(timezone.utc) - timedelta(seconds=10000)
    db_session.commit()

    count = DocumentTaskService(db_session).recover_interrupted(timeout_seconds=300)
    assert count == 1

    res = client.get(f"/api/v1/document-tasks/{task_id}")
    data = res.json()["data"]
    assert data["status"] == "failed"
    assert "中断" in (data["error_message"] or "")


def test_recover_ignores_recent_processing(client: TestClient, db_session) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    task_id = _latest_task(client)["id"]

    t = db_session.get(DocumentTask, task_id)
    t.status = TaskStatus.PROCESSING
    t.started_at = datetime.now(timezone.utc)
    db_session.commit()

    count = DocumentTaskService(db_session).recover_interrupted(timeout_seconds=300)
    assert count == 0


# ---------- 幂等 ----------


def test_idempotent_request_id_prevents_duplicate(
    client: TestClient,
) -> None:
    kb = _create_kb(client)
    request_id = "req-abc-123"

    doc1 = _upload(client, kb["id"], request_id=request_id)
    doc2 = _upload(client, kb["id"], request_id=request_id)

    # 同一 request_id 不产生重复文档/任务
    assert doc1["id"] == doc2["id"]
    tasks = client.get("/api/v1/document-tasks").json()["data"]
    assert len(tasks) == 1


def test_requests_without_id_create_separate_tasks(client: TestClient) -> None:
    kb = _create_kb(client)
    _upload(client, kb["id"])
    _upload(client, kb["id"], name="another.md")

    tasks = client.get("/api/v1/document-tasks").json()["data"]
    assert len(tasks) == 2
