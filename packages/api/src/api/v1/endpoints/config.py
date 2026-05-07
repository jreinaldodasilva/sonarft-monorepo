"""
Parameters and Indicators configuration endpoints.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ....core.limiter import limiter
from ....core.security import get_client_id, require_auth
from ....models.schemas import ClientParametersConfig, IndicatorsConfig, MessageResponse
from ....services.config_service import (
    ConfigService,
    get_config_service_from_state,
)

_SUNSET_DATE = "Sun, 01 Jan 2026 00:00:00 GMT"


def _deprecation_headers(response: Response) -> None:
    """Inject Deprecation and Sunset headers on every legacy response."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _SUNSET_DATE


router = APIRouter(
    tags=["Configuration (Legacy — use /clients/{client_id}/parameters]"],
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
Auth = Annotated[None, Depends(require_auth)]
ClientId = Annotated[str, Depends(get_client_id)]
CfgSvc = Annotated[ConfigService, Depends(get_config_service_from_state)]


# ### Parameters ###

@router.get("/parameters/defaults", response_model=ClientParametersConfig)
@limiter.limit("60/minute")
async def get_default_parameters(
    request: Request,
    _: Auth,
    service: CfgSvc,
) -> ClientParametersConfig:
    """Get default trading parameters."""
    return await service.get_default_parameters()


@router.get("/parameters", response_model=ClientParametersConfig)
@limiter.limit("60/minute")
async def get_parameters(
    request: Request,
    client_id: ClientId,
    service: CfgSvc,
) -> ClientParametersConfig:
    """Get per-client trading parameters."""
    return await service.get_parameters(client_id)


@router.put("/parameters", response_model=MessageResponse)
@limiter.limit("30/minute")
async def update_parameters(
    request: Request,
    client_id: ClientId,
    body: ClientParametersConfig,
    service: CfgSvc,
) -> MessageResponse:
    """Update per-client trading parameters."""
    await service.update_parameters(client_id, body)
    return MessageResponse(message=f"Parameters for {client_id} updated.")


# ### Indicators ###

@router.get("/indicators/defaults", response_model=IndicatorsConfig)
@limiter.limit("60/minute")
async def get_default_indicators(
    request: Request,
    _: Auth,
    service: CfgSvc,
) -> IndicatorsConfig:
    """Get default indicator settings."""
    return await service.get_default_indicators()


@router.get("/indicators", response_model=IndicatorsConfig)
@limiter.limit("60/minute")
async def get_indicators(
    request: Request,
    client_id: ClientId,
    service: CfgSvc,
) -> IndicatorsConfig:
    """Get per-client indicator settings."""
    return await service.get_indicators(client_id)


@router.put("/indicators", response_model=MessageResponse)
@limiter.limit("30/minute")
async def update_indicators(
    request: Request,
    client_id: ClientId,
    body: IndicatorsConfig,
    service: CfgSvc,
) -> MessageResponse:
    """Update per-client indicator settings."""
    await service.update_indicators(client_id, body)
    return MessageResponse(message=f"Indicators for {client_id} updated.")
