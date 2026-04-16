"""
Parameters and Indicators configuration endpoints.
"""
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends

from ....core.security import require_auth
from ....models.schemas import ParametersConfig, IndicatorsConfig, MessageResponse
from ....services.config_service import ConfigService, get_config_service

router = APIRouter(tags=["Configuration"])
Auth = Annotated[None, Depends(require_auth)]


# ### Parameters ###

@router.get("/parameters/defaults", response_model=ParametersConfig)
async def get_default_parameters(
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> ParametersConfig:
    """Get default trading parameters."""
    return await service.get_default_parameters()


@router.get("/parameters", response_model=ParametersConfig)
async def get_parameters(
    client_id: str,
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> ParametersConfig:
    """Get per-client trading parameters."""
    return await service.get_parameters(client_id)


@router.put("/parameters", response_model=MessageResponse)
async def update_parameters(
    client_id: str,
    body: ParametersConfig,
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> MessageResponse:
    """Update per-client trading parameters."""
    await service.update_parameters(client_id, body)
    return MessageResponse(message=f"Parameters for {client_id} updated.")


# ### Indicators ###

@router.get("/indicators/defaults", response_model=IndicatorsConfig)
async def get_default_indicators(
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> IndicatorsConfig:
    """Get default indicator settings."""
    return await service.get_default_indicators()


@router.get("/indicators", response_model=IndicatorsConfig)
async def get_indicators(
    client_id: str,
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> IndicatorsConfig:
    """Get per-client indicator settings."""
    return await service.get_indicators(client_id)


@router.put("/indicators", response_model=MessageResponse)
async def update_indicators(
    client_id: str,
    body: IndicatorsConfig,
    _: Auth,
    service: ConfigService = Depends(get_config_service),
) -> MessageResponse:
    """Update per-client indicator settings."""
    await service.update_indicators(client_id, body)
    return MessageResponse(message=f"Indicators for {client_id} updated.")
