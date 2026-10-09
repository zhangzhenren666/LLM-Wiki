"""数据库模型包。

导入所有模型以注册到 SQLAlchemy metadata，供建表与迁移使用。
"""
from app.models.base import Base, TimestampMixin, utcnow
from app.models.document import Document, ImportStatus
from app.models.document_task import DocumentTask, StepStatus, TaskStatus, TaskStep
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_item import KnowledgeItem, KnowledgeItemStatus
from app.models.model_config import ModelConfig
from app.models.page_relation import PageRelation, RelationSource, RelationType
from app.models.page_tag import PageTag
from app.models.relation_anomaly import AnomalyStatus, AnomalyType, RelationAnomaly
from app.models.wiki_page import PageStatus, WikiPage

__all__ = [
    "Base",
    "TimestampMixin",
    "utcnow",
    "KnowledgeBase",
    "WikiPage",
    "PageStatus",
    "PageTag",
    "PageRelation",
    "RelationType",
    "RelationSource",
    "Document",
    "ImportStatus",
    "ModelConfig",
    "DocumentTask",
    "TaskStatus",
    "StepStatus",
    "TaskStep",
    "KnowledgeItem",
    "KnowledgeItemStatus",
    "RelationAnomaly",
    "AnomalyType",
    "AnomalyStatus",
]
