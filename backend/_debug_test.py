"""临时调试脚本 — 模拟后端请求是否挂起。"""
from app.main import app
from fastapi.testclient import TestClient

with TestClient(app) as c:
    print("STARTING request to /api/v1/model-configs ...")
    r = c.get("/api/v1/model-configs", timeout=5)
    print("DONE. status=", r.status_code)
    print(r.text[:300])
    print("---")
    r2 = c.get("/api/v1/knowledge-bases", timeout=5)
    print("KB DONE. status=", r2.status_code)
print("ALL GOOD")