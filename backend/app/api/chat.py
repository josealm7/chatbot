from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_engine import chat
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, req: ChatRequest):
    """
    Endpoint principal de chat.
    Límite: 20 mensajes por minuto por IP.
    """
    try:
        response = await chat(
            session_id=req.session_id,
            user_message=req.message,
            company_id=req.company_id,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail="Error al procesar el mensaje. Inténtalo de nuevo.")


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Limpia el historial de conversación de una sesión."""
    from app.services.memory import session_store
    session_store.clear_session(session_id)
    return {"status": "ok", "session_id": session_id}