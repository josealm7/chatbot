from fastapi import APIRouter, HTTPException
from app.models.schemas import CompanyConfig, CompanyConfigResponse
from app.services.company_config import config_store

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/{company_id}", response_model=CompanyConfigResponse)
async def get_config(company_id: str):
    """Obtiene la configuración de una empresa."""
    config = config_store.get(company_id)
    return CompanyConfigResponse(status="ok", config=config)


@router.post("", response_model=CompanyConfigResponse)
async def create_or_update_config(config: CompanyConfig):
    """Crea o actualiza la configuración de una empresa/bot."""
    config_store.set(config)
    return CompanyConfigResponse(status="ok", config=config)


@router.get("", response_model=list[CompanyConfig])
async def list_configs():
    """Lista todas las configuraciones de empresa."""
    return config_store.list_all()
