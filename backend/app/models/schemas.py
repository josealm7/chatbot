from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import re


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64,
                            description="ID único de sesión del usuario")
    message: str = Field(..., min_length=1, max_length=2000)
    company_id: str = Field(default="default", max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        # Solo alfanuméricos, guiones y guiones bajos — sin inyecciones
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("session_id solo puede contener letras, números, _ y -")
        return v

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("company_id solo puede contener letras, números, _ y -")
        return v


class Source(BaseModel):
    file: str
    page: Optional[int] = None
    snippet: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source] = []
    fallback: bool = False
    fallback_reason: Optional[str] = None
    confidence: float = 1.0


# ── Documents ─────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int
    files_processed: list[str]
    company_id: str


class DeleteDocumentsResponse(BaseModel):
    status: str
    company_id: str


# ── Company Config ────────────────────────────────────────────────────────────

class CompanyConfig(BaseModel):
    company_id: str = Field(default="default")
    company_name: str = Field(default="Mi Empresa S.L.")
    bot_name: str = Field(default="Asistente Virtual")
    industry: str = Field(default="seguros")
    system_role: str = Field(
        default=(
            "Eres un asistente de soporte de {company_name}. "
            "Responde siempre en español, de forma clara y amable. "
            "Usa solo la información proporcionada en los documentos. "
            "Si no tienes información suficiente, dilo honestamente."
        )
    )
    fallback_message: str = Field(
        default=(
            "No tengo información suficiente sobre eso. "
            "¿Te gustaría que te pusiera en contacto con un agente humano?"
        )
    )
    handoff_message: str = Field(
        default=(
            "Entendido. Voy a transferirte con uno de nuestros agentes. "
            "Un momento por favor. 🙋"
        )
    )
    escalation_keywords: list[str] = Field(
        default=["hablar con humano", "agente", "persona real", "representante", "queja formal"]
    )


class CompanyConfigResponse(BaseModel):
    status: str
    config: CompanyConfig


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    vector_store: str
    documents_indexed: int
    version: str = "1.0.0"