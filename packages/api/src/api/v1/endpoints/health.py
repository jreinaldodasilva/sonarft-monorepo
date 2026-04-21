from fastapi import APIRouter

from ....models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Service health check."""
    return HealthResponse()
