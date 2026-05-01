from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_engine import chat
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Endpoint principal de chat.
    Recibe mensaje + session_id, devuelve respuesta con fuentes.
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
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Limpia el historial de conversación de una sesión."""
    from app.services.memory import session_store
    session_store.clear_session(session_id)
    return {"status": "ok", "session_id": session_id}
