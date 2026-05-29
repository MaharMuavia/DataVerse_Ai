"""AI catalog routes for model selection and prompt guidance."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..api.schemas import User
from ..core.auth import get_current_user
from ..services.model_catalog import get_model_catalog, get_prompt_profiles

router = APIRouter()


@router.get("/catalog", response_model=dict)
async def get_ai_catalog(
    current_user: User = Depends(get_current_user),  # noqa: ARG001 - authenticated product surface
):
    return {
        "catalog": get_model_catalog(),
        "prompt_profiles": get_prompt_profiles(),
    }
