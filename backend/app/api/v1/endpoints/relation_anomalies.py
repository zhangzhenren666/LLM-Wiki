"""关系异常记录接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.relation_anomaly import RelationAnomalyListResponse, RelationAnomalyRead
from app.services.relation_extraction import RelationExtractionService

router = APIRouter(prefix="/relation-anomalies", tags=["relation-anomalies"])


def _service(db: Session = Depends(get_db)) -> RelationExtractionService:
    return RelationExtractionService(db)


@router.get("/tasks/{task_id}", response_model=ApiResponse[RelationAnomalyListResponse])
def list_anomalies_by_task(
    task_id: int,
    service: RelationExtractionService = Depends(_service),
) -> ApiResponse[RelationAnomalyListResponse]:
    """查询某任务的所有关系异常记录。"""
    items = service.get_anomalies_for_task(task_id)
    reads = [RelationAnomalyRead.model_validate(item) for item in items]

    return success(
        data=RelationAnomalyListResponse(
            items=reads,
            total=len(reads),
        ),
        message="ok",
    )