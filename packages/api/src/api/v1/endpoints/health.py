from fastapi import APIRouter, HTTPException, Request

from ....models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Service liveness check."""
    return HealthResponse()


@router.get("/health/ready", tags=["Health"])
async def ready(request: Request) -> dict:
    """Service readiness check — returns 503 if any service failed to initialise."""
    bot_ok = getattr(request.app.state, "bot_service", None) is not None
    cfg_ok = getattr(request.app.state, "config_service", None) is not None
    if not bot_ok or not cfg_ok:
        raise HTTPException(status_code=503, detail="Services not ready")
    return {"status": "ready"}
