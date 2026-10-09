"""api.v1 包：v1 版本接口。"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    documents,
    document_tasks,
    graph,
    health,
    knowledge_bases,
    knowledge_items,
    model_configs,
    pages,
    relation_anomalies,
    relations,
    search,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(pages.router)
api_router.include_router(relations.router)
api_router.include_router(graph.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(model_configs.router)
api_router.include_router(document_tasks.router)
api_router.include_router(knowledge_items.router)
api_router.include_router(relation_anomalies.router)
