"""
Session Memory Service
Gestiona el historial de conversación por sesión.
Usa memoria en RAM (dict) — para producción, usar Redis.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

# Máximo de turnos a recordar (más → más tokens → más caro)
MAX_HISTORY_TURNS = 10
# Expiración de sesión inactiva
SESSION_TTL_MINUTES = 60


class SessionStore:
    """
    Almacén de sesiones en memoria.
    En producción, sustituir por RedisChat o DynamoDB.
    """

    def __init__(self):
        self._sessions: dict[str, list[BaseMessage]] = defaultdict(list)
        self._last_active: dict[str, datetime] = {}

    def get_history(self, session_id: str) -> list[BaseMessage]:
        self._cleanup_expired()
        return self._sessions.get(session_id, [])

    def add_turn(self, session_id: str, user_msg: str, ai_msg: str) -> None:
        history = self._sessions[session_id]
        history.append(HumanMessage(content=user_msg))
        history.append(AIMessage(content=ai_msg))

        # Mantener solo los últimos N turnos
        if len(history) > MAX_HISTORY_TURNS * 2:
            self._sessions[session_id] = history[-(MAX_HISTORY_TURNS * 2):]

        self._last_active[session_id] = datetime.utcnow()
        logger.debug(f"Session {session_id}: {len(self._sessions[session_id])//2} turns stored")

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._last_active.pop(session_id, None)

    def get_summary(self, session_id: str) -> str:
        """Devuelve un resumen textual del historial para insertar en el prompt."""
        history = self.get_history(session_id)
        if not history:
            return ""

        lines = []
        for msg in history:
            role = "Usuario" if isinstance(msg, HumanMessage) else "Asistente"
            lines.append(f"{role}: {msg.content}")

        return "\n".join(lines)

    def _cleanup_expired(self) -> None:
        cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TTL_MINUTES)
        expired = [sid for sid, t in self._last_active.items() if t < cutoff]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._last_active.pop(sid, None)
        if expired:
            logger.info(f"Expired {len(expired)} sessions")

    @property
    def active_sessions(self) -> int:
        return len(self._sessions)


# Singleton global
session_store = SessionStore()
