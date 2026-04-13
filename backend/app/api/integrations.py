from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.integration import ServiceDetail, ServiceSummary
from app.services.service_connections import get_service_detail, list_service_summaries

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/services", response_model=list[ServiceSummary])
def list_services(
    current_user: User = Depends(get_current_user),
):
    return list_service_summaries(current_user)


@router.get("/services/{service_key}", response_model=ServiceDetail)
def service_details(
    service_key: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return get_service_detail(current_user, service_key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Service not found")
