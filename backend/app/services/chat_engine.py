"""
RAG Chat Engine
El corazón del sistema: retrieval + generation con LangChain + Groq.

Flujo por mensaje:
1. Detectar si el usuario pide hablar con humano → escalation
2. Recuperar docs relevantes del vector store
3. Evaluar confianza (score de similitud)
4. Construir prompt con: role, historial, contexto docs, pregunta
5. Llamar a Groq (llama-3.1-8b-instant)
6. Devolver respuesta + fuentes + flags
"""
from __future__ import annotations

import logging
from typing import Optional


from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import get_settings
from app.models.schemas import ChatResponse, Source, CompanyConfig
from app.services.vector_store import get_vector_store
from app.services.memory import session_store
from app.services.company_config import config_store

logger = logging.getLogger(__name__)
settings = get_settings()


# ── LLM singleton ─────────────────────────────────────────────────────────────

def get_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.model_name,
        api_key=settings.groq_api_key,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_TEMPLATE = """Eres {bot_name}, el asistente virtual de {company_name}.

{role_description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCCIONES IMPORTANTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Responde SIEMPRE en español, de forma clara y profesional.
2. Basa tus respuestas ÚNICAMENTE en la información del contexto proporcionado.
3. CRÍTICO: Si el contexto de documentos está vacío o dice "Sin información relevante disponible", responde ÚNICAMENTE: "No tengo información sobre eso todavía. Por favor, carga los documentos de la empresa para que pueda ayudarte." No inventes NUNCA servicios, precios ni información de la empresa.
4. Sé conciso pero completo. Usa bullet points cuando ayude a la claridad.
5. Nunca inventes datos, precios, políticas o información que no esté en el contexto.
6. Si el usuario parece frustrado, muestra empatía antes de responder.
7. Recuerda el historial de la conversación para dar respuestas coherentes.
8. Si el usuario responde con palabras cortas como "sí", "no", "vale", "gracias", interpreta su respuesta en el contexto de la conversación anterior y responde coherentemente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO DE LA EMPRESA (documentos):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si el contexto está vacío o no es relevante responde:
"{fallback_message}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

NO_CONTEXT_RESPONSE = "__NO_CONTEXT__"


# ── Escalation detection ──────────────────────────────────────────────────────

def _detect_escalation(message: str, config: CompanyConfig) -> bool:
    """Detecta si el usuario quiere hablar con un humano."""
    msg_lower = message.lower()
    return any(kw.lower() in msg_lower for kw in config.escalation_keywords)


# ── Main chat function ────────────────────────────────────────────────────────

async def chat(
    session_id: str,
    user_message: str,
    company_id: str = "default",
) -> ChatResponse:

    config = config_store.get(company_id)

    # 1. ¿Escalation? (usuario pide agente humano)
    if _detect_escalation(user_message, config):
        session_store.add_turn(session_id, user_message, config.handoff_message)
        return ChatResponse(
            session_id=session_id,
            answer=config.handoff_message,
            fallback=True,
            fallback_reason="escalation",
            confidence=1.0,
        )

    # 2. Recuperar documentos relevantes
    store = get_vector_store(company_id)
    results = store.similarity_search_with_score(user_message, k=settings.retrieval_k)

    # 3. Evaluar confianza y filtrar docs
    relevant_results = [
        (doc, score)
        for doc, score in results
        if score >= settings.similarity_threshold
    ]

    is_conversational = len(user_message.strip().split()) <= 3

    has_context = bool(relevant_results) or is_conversational
    avg_confidence = (
        sum(s for _, s in relevant_results) / len(relevant_results)
        if relevant_results else 0.0
    )

    # Construir bloque de contexto
    if has_context:
        context_parts = []
        for i, (doc, score) in enumerate(relevant_results, 1):
            src = doc.metadata.get("source_file", "documento")
            page = doc.metadata.get("page", "")
            page_str = f" (pág. {page + 1})" if page != "" else ""
            context_parts.append(
                f"[Fuente {i}: {src}{page_str}]\n{doc.page_content.strip()}"
            )
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "Sin información relevante disponible."

    # 4. Obtener historial de la sesión
    history = session_store.get_history(session_id)

    # 5. Construir mensajes para Claude
    system_content = SYSTEM_TEMPLATE.format(
        bot_name=config.bot_name,
        company_name=config.company_name,
        role_description=config.system_role.format(company_name=config.company_name),
        context=context_str,
        fallback_message=config.fallback_message,
    )

    messages = [SystemMessage(content=system_content)]
    messages.extend(history)
    messages.append(HumanMessage(content=user_message))

    # 6. Llamar al LLM
    llm = get_llm()
    try:
        response = await llm.ainvoke(messages)
        answer = response.content

        # Si el modelo devuelve la señal de no-contexto, usar fallback
        if NO_CONTEXT_RESPONSE in answer or (not has_context):
            final_answer = config.fallback_message if (not has_context and not is_conversational) else answer
            fallback = not has_context and not is_conversational
            fallback_reason = "no_context" if (not has_context and not is_conversational) else None
        else:
            final_answer = answer
            fallback = False
            fallback_reason = None

    except Exception as e:
        logger.error(f"LLM error: {e}")
        final_answer = "Lo siento, ha ocurrido un error técnico. Por favor, inténtalo de nuevo."
        fallback = True
        fallback_reason = "llm_error"
        avg_confidence = 0.0

    # 7. Guardar en historial
    session_store.add_turn(session_id, user_message, final_answer)

    # 8. Construir fuentes para el frontend
    sources = []
    if has_context and not fallback:
        seen = set()
        for doc, score in relevant_results[:3]:
            src_file = doc.metadata.get("source_file", "documento")
            if src_file in seen:
                continue
            seen.add(src_file)
            sources.append(Source(
                file=src_file,
                page=doc.metadata.get("page"),
                snippet=doc.page_content[:120].strip() + "…",
            ))

    return ChatResponse(
        session_id=session_id,
        answer=final_answer,
        sources=sources,
        fallback=fallback,
        fallback_reason=fallback_reason,
        confidence=round(avg_confidence, 3),
    )
