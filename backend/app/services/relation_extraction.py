"""知识关系自动提取服务。

新知识页面创建后，自动识别其与现有页面的关系：
- 有明确依据的关系自动入图
- 不确定、冲突或缺少依据的情况记录为异常
"""

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.document import Document
from app.models.document_task import DocumentTask
from app.models.knowledge_item import KnowledgeItem, KnowledgeItemStatus
from app.models.model_config import ModelConfig
from app.models.page_relation import PageRelation, RelationSource, RelationType
from app.models.relation_anomaly import AnomalyStatus, AnomalyType, RelationAnomaly
from app.models.wiki_page import WikiPage
from app.repositories.model_config import ModelConfigRepository
from app.repositories.relation import check_duplicate, create_auto
from app.services.llm import ChatMessage, LLMClient, ModelCallError
from app.services.search import search as search_service

logger = get_logger(__name__)

# 关系类型名称 → 枚举映射（用于模型输出校验）
RELATION_TYPE_MAP: dict[str, RelationType] = {
    "related": RelationType.RELATED,
    "related_to": RelationType.RELATED,
    "part_of": RelationType.PART_OF,
    "depends_on": RelationType.DEPENDS_ON,
    "explains": RelationType.EXPLAINS,
    "reference": RelationType.REFERENCE,
    "references": RelationType.REFERENCES,
}

# 每页最多候选数
MAX_CANDIDATES_PER_PAGE = 10
# 候选页面检索关键词数
MAX_SEARCH_KEYWORDS = 3


# ---------------------------------------------------------------------------
# 候选页面检索
# ---------------------------------------------------------------------------

def _find_candidate_pages(
    db: Session,
    page: WikiPage,
    tags: list[str] | None,
    exclude_page_id: int,
) -> list[WikiPage]:
    """为新页面查找可能相关的候选现有页面。

    策略：标题关键词搜索 + 标签匹配 + 内容关键词搜索，去重后限制数量。
    """
    candidates: dict[int, WikiPage] = {}
    kb_id = page.knowledge_base_id

    # 1. 标题关键词搜索
    keywords = _extract_title_keywords(page.title)
    for kw in keywords[:MAX_SEARCH_KEYWORDS]:
        try:
            result = search_service(db, query=kw, knowledge_base_id=kb_id, page=1, page_size=5)
            for item in result.items:
                if item.page_id != exclude_page_id and item.page_id not in candidates:
                    p = db.get(WikiPage, item.page_id)
                    if p is not None:
                        candidates[item.page_id] = p
        except ValueError:
            pass

    # 2. 标签匹配
    if tags:
        for tag in tags[:3]:
            if tag.strip():
                from app.repositories.page import list_pages
                tag_pages = list_pages(db, knowledge_base_id=kb_id, tag=tag.strip())
                for p in tag_pages:
                    if p.id != exclude_page_id and p.id not in candidates:
                        candidates[p.id] = p

    # 3. 限制数量
    result_list = list(candidates.values())
    if len(result_list) > MAX_CANDIDATES_PER_PAGE:
        result_list = result_list[:MAX_CANDIDATES_PER_PAGE]

    return result_list


def _extract_title_keywords(title: str) -> list[str]:
    """从标题中提取关键词。"""
    # 提取中文词（>=2字）和英文单词（>=3字母）
    words = re.findall(r"[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}", title)
    return words[:10]


# ---------------------------------------------------------------------------
# 提示词构建
# ---------------------------------------------------------------------------

_RELATION_SYSTEM_PROMPT = (
    "你是一个知识关系分析专家。请评估新生成的 Wiki 页面与现有页面之间的关系。\n"
    "\n"
    "可用的关系类型（严格限定，不得创造新类型）：\n"
    "- related: 相关内容或主题相近\n"
    "- part_of: 新页面是目标页面的组成部分\n"
    "- depends_on: 新页面依赖目标页面的知识\n"
    "- explains: 新页面解释或说明目标页面的内容\n"
    "- reference: 新页面引用了目标页面\n"
    "\n"
    "要求：\n"
    "1. 只返回有明确依据的关系，不要猜测或编造。\n"
    "2. 每条关系必须包含：source_page_id（新页面ID）、target_page_id（候选页面ID）、"
    "relation_type（仅限上述类型）、reason（简短理由）、evidence（支持关系的文本依据）。\n"
    "3. 如果找不到任何明确关系，返回空的 relations 列表。\n"
    "4. 不要使用不存在的页面ID。\n"
    "\n"
    "返回严格的 JSON 格式：\n"
    '{"relations": [{"source_page_id": 1, "target_page_id": 2, "relation_type": "related", '
    '"reason": "...", "evidence": "..."}]}'
)


def _build_relation_user_prompt(
    source_page: WikiPage,
    candidates: list[WikiPage],
    tags: list[str] | None,
) -> str:
    """构建关系分析的用户提示词。"""
    parts: list[str] = []

    # 新页面信息
    parts.append("## 新生成的页面")
    parts.append(f"- ID: {source_page.id}")
    parts.append(f"- 标题: {source_page.title}")
    # 正文截取前500字符
    content_preview = (source_page.content or "")[:500]
    parts.append(f"- 正文摘要: {content_preview}")
    if tags:
        parts.append(f"- 标签: {', '.join(tags)}")

    parts.append("")
    parts.append("## 候选现有页面")
    for i, c in enumerate(candidates):
        parts.append(f"### 候选 {i + 1}")
        parts.append(f"- ID: {c.id}")
        parts.append(f"- 标题: {c.title}")
        c_preview = (c.content or "")[:300]
        parts.append(f"- 正文摘要: {c_preview}")
        c_tags = [t.tag_name for t in c.tags] if c.tags else []
        if c_tags:
            parts.append(f"- 标签: {', '.join(c_tags)}")

    parts.append("")
    parts.append("请分析上述新页面与各候选页面之间的关系，返回 JSON。")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# JSON 解析与校验
# ---------------------------------------------------------------------------

def _extract_json_from_response(raw: str) -> dict[str, Any]:
    """从模型响应中提取 JSON 对象。"""
    if not raw or not raw.strip():
        raise AppError("模型返回了空响应", code=502, status_code=502)

    text = raw.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_match:
        try:
            return json.loads(code_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise AppError("模型返回的内容无法解析为 JSON", code=502, status_code=502)


def _validate_relation_suggestion(
    suggestion: dict[str, Any],
    source_page_id: int,
    valid_candidate_ids: set[int],
    kb_id: int,
    db: Session,
) -> tuple[dict[str, Any] | None, str | None]:
    """校验单条关系建议。

    返回 (validated_dict, anomaly_reason)。
    validated_dict 非空表示通过校验可入库；
    anomaly_reason 非空表示存在问题。
    """
    if not isinstance(suggestion, dict):
        return None, "模型返回的关系条目格式异常"

    # 1. 源页面校验
    sug_source = suggestion.get("source_page_id")
    try:
        sug_source = int(sug_source) if sug_source is not None else None
    except (ValueError, TypeError):
        return None, f"无效的 source_page_id: {sug_source}"

    if sug_source != source_page_id:
        return None, f"source_page_id 不匹配（期望 {source_page_id}，得到 {sug_source}）"

    # 2. 目标页面校验
    sug_target = suggestion.get("target_page_id")
    try:
        sug_target = int(sug_target) if sug_target is not None else None
    except (ValueError, TypeError):
        return None, f"无效的 target_page_id: {sug_target}"

    if sug_target is None:
        return None, "缺少 target_page_id"

    if sug_target not in valid_candidate_ids:
        return None, f"target_page_id {sug_target} 不在候选页面列表中"

    if sug_target == sug_source:
        return None, "不能与自身建立关系"

    # 验证目标页面存在且在同一知识库
    target_page = db.get(WikiPage, sug_target)
    if target_page is None:
        return None, f"目标页面不存在: id={sug_target}"
    if target_page.knowledge_base_id != kb_id:
        return None, "目标页面与源页面不属于同一知识库"

    # 3. 关系类型校验
    raw_type = (suggestion.get("relation_type") or "").strip().lower()
    rel_type = RELATION_TYPE_MAP.get(raw_type)
    if rel_type is None:
        return None, f"不支持的关系类型: {raw_type}"

    # 4. 理由和证据校验
    reason = (suggestion.get("reason") or "").strip()
    evidence = (suggestion.get("evidence") or "").strip()

    if not reason or len(reason) < 3:
        return None, "缺少关系创建理由或理由过于简短"

    if not evidence or len(evidence) < 5:
        return None, "缺少支持关系的文本依据"

    # 5. 重复检查
    existing = check_duplicate(db, sug_source, sug_target, rel_type)
    if existing is not None:
        return None, f"关系已存在: {sug_source} -> {sug_target} ({rel_type.value})"

    return {
        "source_page_id": sug_source,
        "target_page_id": sug_target,
        "relation_type": rel_type,
        "reason": reason[:500],
        "evidence": evidence[:2000],
    }, None


# ---------------------------------------------------------------------------
# 主服务类
# ---------------------------------------------------------------------------

class RelationExtractionService:
    """知识关系自动提取服务。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._model_config_repo = ModelConfigRepository(db)

    def extract_and_create_relations(self, task: DocumentTask) -> dict[str, int]:
        """为新生成的 Wiki 页面自动识别并创建关系。

        返回统计: {created, skipped, anomaly}
        """
        # 1. 获取该任务中自动创建的页面
        stmt = (
            select(KnowledgeItem)
            .where(
                KnowledgeItem.task_id == task.id,
                KnowledgeItem.status == KnowledgeItemStatus.AUTO_CREATED,
                KnowledgeItem.wiki_page_id.isnot(None),
            )
            .order_by(KnowledgeItem.id)
        )
        items = list(self._db.execute(stmt).scalars().all())

        if not items:
            logger.info("任务无自动创建的页面，跳过关系构建 task_id=%s", task.id)
            return {"created": 0, "skipped": 0, "anomaly": 0}

        # 2. 获取可用模型配置
        model_cfg = self._get_active_model_config()
        if model_cfg is None:
            logger.warning("无可用模型配置，跳过关系构建 task_id=%s", task.id)
            return {"created": 0, "skipped": 0, "anomaly": 0}

        api_key = decrypt_secret(model_cfg.api_key_encrypted)
        if not api_key:
            logger.warning("模型配置未设置 API Key，跳过关系构建 task_id=%s", task.id)
            return {"created": 0, "skipped": 0, "anomaly": 0}

        task.model_config_id = model_cfg.id

        client = LLMClient(
            base_url=model_cfg.base_url,
            api_key=api_key,
            model=model_cfg.model_name,
            timeout=model_cfg.timeout_seconds,
        )

        kb_id = task.knowledge_base_id
        stats = {"created": 0, "skipped": 0, "anomaly": 0}

        # 3. 逐页面处理
        for item in items:
            page = self._db.get(WikiPage, item.wiki_page_id)
            if page is None:
                continue

            # 解析标签
            tags: list[str] | None = None
            if item.tags:
                try:
                    tags = json.loads(item.tags)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 查找候选页面
            candidates = _find_candidate_pages(self._db, page, tags, page.id)
            if not candidates:
                logger.info("页面无候选页面，跳过关系构建 page_id=%s", page.id)
                stats["skipped"] += 1
                continue

            # 调用模型
            messages: list[ChatMessage] = [
                {"role": "system", "content": _RELATION_SYSTEM_PROMPT},
                {"role": "user", "content": _build_relation_user_prompt(page, candidates, tags)},
            ]

            try:
                raw_response = client.chat(messages)
            except ModelCallError as exc:
                logger.error("关系分析模型调用失败 page_id=%s: %s", page.id, exc.message)
                self._record_anomaly(
                    task=task,
                    kb_id=kb_id,
                    anomaly_type=AnomalyType.MODEL_OUTPUT_ERROR,
                    source_page_id=page.id,
                    reason=f"模型调用失败: {exc.message}",
                    suggestion="检查模型配置后重试任务",
                )
                stats["anomaly"] += 1
                continue

            # 解析响应
            try:
                data = _extract_json_from_response(raw_response)
            except AppError as exc:
                self._record_anomaly(
                    task=task,
                    kb_id=kb_id,
                    anomaly_type=AnomalyType.MODEL_OUTPUT_ERROR,
                    source_page_id=page.id,
                    reason=f"模型响应解析失败: {exc.message}",
                    suggestion="重试任务或检查模型输出格式",
                )
                stats["anomaly"] += 1
                continue

            relations_raw = data.get("relations", [])
            if not isinstance(relations_raw, list) or len(relations_raw) == 0:
                stats["skipped"] += 1
                continue

            valid_candidate_ids = {c.id for c in candidates}

            for rel_raw in relations_raw:
                validated, anomaly_reason = _validate_relation_suggestion(
                    rel_raw, page.id, valid_candidate_ids, kb_id, self._db,
                )

                if anomaly_reason:
                    self._record_anomaly(
                        task=task,
                        kb_id=kb_id,
                        anomaly_type=self._classify_anomaly(anomaly_reason),
                        source_page_id=page.id,
                        target_page_id=_safe_get_target_id(rel_raw),
                        reason=anomaly_reason,
                        evidence=(rel_raw if isinstance(rel_raw, dict) else {}).get("evidence"),
                        suggestion=self._suggest_action(anomaly_reason),
                    )
                    stats["anomaly"] += 1
                    continue

                # 创建关系
                try:
                    create_auto(
                        self._db,
                        knowledge_base_id=kb_id,
                        source_page_id=validated["source_page_id"],
                        target_page_id=validated["target_page_id"],
                        relation_type=validated["relation_type"],
                        reason=validated["reason"],
                        evidence=validated["evidence"],
                    )
                    stats["created"] += 1
                    logger.info(
                        "自动创建关系 page_id=%s -> %s type=%s",
                        validated["source_page_id"],
                        validated["target_page_id"],
                        validated["relation_type"].value,
                    )
                except Exception as exc:
                    logger.exception("创建关系失败")
                    self._record_anomaly(
                        task=task,
                        kb_id=kb_id,
                        anomaly_type=AnomalyType.MODEL_OUTPUT_ERROR,
                        source_page_id=validated["source_page_id"],
                        target_page_id=validated["target_page_id"],
                        reason=f"数据库写入失败: {str(exc)[:200]}",
                        suggestion="检查数据库状态后重试",
                    )
                    stats["anomaly"] += 1

        return stats

    # ---------- 内部方法 ----------

    def _get_active_model_config(self) -> ModelConfig | None:
        """获取可用的模型配置。

        优先默认配置，否则取第一个已启用的配置。
        """
        cfg = self._model_config_repo.get_default()
        if cfg is not None and cfg.is_active:
            return cfg
        # 没有默认配置或默认配置被停用 → 找第一个启用的
        all_cfgs = self._model_config_repo.list()
        for c in all_cfgs:
            if c.is_active:
                return c
        return None

    def _record_anomaly(
        self,
        *,
        task: DocumentTask,
        kb_id: int,
        anomaly_type: AnomalyType,
        source_page_id: int | None = None,
        target_page_id: int | None = None,
        reason: str,
        evidence: str | None = None,
        suggestion: str | None = None,
    ) -> RelationAnomaly:
        """记录一条关系异常。"""
        anomaly = RelationAnomaly(
            task_id=task.id,
            knowledge_base_id=kb_id,
            anomaly_type=anomaly_type,
            source_page_id=source_page_id,
            target_page_id=target_page_id,
            reason=reason[:2000],
            evidence=(evidence or "")[:2000] if evidence else None,
            suggestion=(suggestion or "")[:500] if suggestion else None,
            status=AnomalyStatus.PENDING,
        )
        self._db.add(anomaly)
        return anomaly

    def _classify_anomaly(self, reason: str) -> AnomalyType:
        """根据异常原因文字判断异常类型。"""
        r = reason.lower()
        if "重复" in r or "已存在" in r:
            return AnomalyType.DUPLICATE_PAGE
        if "冲突" in r or "矛盾" in r:
            return AnomalyType.CONTENT_CONFLICT
        if "缺少" in r or "依据" in r or "证据" in r or "理由" in r:
            return AnomalyType.MISSING_EVIDENCE
        if "类型" in r or "不支持" in r:
            return AnomalyType.RELATION_UNCLEAR
        return AnomalyType.RELATION_UNCLEAR

    def _suggest_action(self, reason: str) -> str:
        """根据异常原因给出处理建议。"""
        r = reason.lower()
        if "重复" in r or "已存在" in r:
            return "查看原文确认是否为同一知识点，若重复可忽略"
        if "缺少" in r or "依据" in r or "证据" in r or "理由" in r:
            return "查看原文，手动补充关系说明后可在页面详情中添加关系"
        if "类型" in r or "不支持" in r:
            return "手动选择合适的关系类型建立连接"
        if "不存在" in r or "不匹配" in r:
            return "模型引用错误，忽略此候选"
        if "模型" in r:
            return "检查模型配置后重试任务"
        return "查看涉及页面原文，手动判断是否建立关系"

    def get_anomalies_for_task(self, task_id: int) -> list[RelationAnomaly]:
        """查询某任务的所有关系异常记录。"""
        stmt = (
            select(RelationAnomaly)
            .where(RelationAnomaly.task_id == task_id)
            .order_by(RelationAnomaly.id)
        )
        return list(self._db.execute(stmt).scalars().all())


def _safe_get_target_id(rel_raw) -> int | None:
    """安全提取 target_page_id。"""
    if not isinstance(rel_raw, dict):
        return None
    try:
        return int(rel_raw.get("target_page_id", 0)) if rel_raw.get("target_page_id") else None
    except (ValueError, TypeError):
        return None