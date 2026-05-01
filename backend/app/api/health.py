from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.vector_store import get_vector_store
from app.services.memory import session_store
from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health():
    try:
        store = get_vector_store("default")
        count = store.count()
    except Exception:
        count = -1

    return HealthResponse(
        status="ok",
        vector_store=settings.vector_store,
        documents_indexed=count,
    )


@router.get("/")
async def root():
    return {
        "name": "SmartChat API",
        "version": "1.0.0",
        "docs": "/docs",
        "active_sessions": session_store.active_sessions,
    }
