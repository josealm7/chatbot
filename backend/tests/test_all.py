"""
Tests — SmartChat Backend
Cubre: schemas, memory, company config, ingestion, chat engine (mocked), API endpoints.
Corre con: pytest tests/ -v
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_md_file(tmp_path_factory):
    """Crea un archivo Markdown de prueba."""
    d = tmp_path_factory.mktemp("docs")
    f = d / "test_doc.md"
    f.write_text(
        "# Manual de prueba\n\n"
        "## Precios\n\nEl plan básico cuesta 20€ al mes.\n\n"
        "## Soporte\n\nEl soporte está disponible de lunes a viernes de 9 a 18h.\n\n"
        "## Contacto\n\nLlama al 900 000 000 o escribe a soporte@empresa.es\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture(scope="session")
def sample_txt_file(tmp_path_factory):
    d = tmp_path_factory.mktemp("docs")
    f = d / "faq.txt"
    f.write_text(
        "¿Cómo cancelo mi suscripción?\n"
        "Puedes cancelar desde tu área de cliente o llamando al soporte.\n\n"
        "¿Tienen prueba gratuita?\n"
        "Sí, ofrecemos 14 días de prueba gratuita sin tarjeta de crédito.\n",
        encoding="utf-8",
    )
    return f


# ── Schema Tests ───────────────────────────────────────────────────────────────

class TestSchemas:
    def test_chat_request_valid(self):
        from app.models.schemas import ChatRequest
        req = ChatRequest(session_id="abc123", message="Hola", company_id="default")
        assert req.session_id == "abc123"
        assert req.message == "Hola"

    def test_chat_request_empty_message_raises(self):
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(session_id="abc", message="", company_id="default")

    def test_chat_request_message_too_long_raises(self):
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(session_id="abc", message="x" * 2001, company_id="default")

    def test_company_config_defaults(self):
        from app.models.schemas import CompanyConfig
        cfg = CompanyConfig()
        assert cfg.company_id == "default"
        assert len(cfg.escalation_keywords) > 0

    def test_chat_response_structure(self):
        from app.models.schemas import ChatResponse
        resp = ChatResponse(
            session_id="s1",
            answer="Hola, puedo ayudarte",
            sources=[],
            fallback=False,
            confidence=0.85,
        )
        assert resp.confidence == 0.85
        assert resp.fallback is False

    def test_source_model(self):
        from app.models.schemas import Source
        s = Source(file="manual.pdf", page=2, snippet="El precio es 20€...")
        assert s.file == "manual.pdf"
        assert s.page == 2


# ── Memory Tests ───────────────────────────────────────────────────────────────

class TestSessionMemory:
    def setup_method(self):
        from app.services.memory import SessionStore
        self.store = SessionStore()

    def test_empty_session_returns_empty_list(self):
        history = self.store.get_history("nonexistent")
        assert history == []

    def test_add_turn_and_retrieve(self):
        self.store.add_turn("s1", "¿Cuánto cuesta?", "El plan básico cuesta 20€/mes.")
        history = self.store.get_history("s1")
        assert len(history) == 2
        assert history[0].content == "¿Cuánto cuesta?"
        assert history[1].content == "El plan básico cuesta 20€/mes."

    def test_multiple_turns_ordered(self):
        self.store.add_turn("s2", "Hola", "¡Hola! ¿En qué puedo ayudarte?")
        self.store.add_turn("s2", "¿Tenéis soporte?", "Sí, de 9 a 18h.")
        history = self.store.get_history("s2")
        assert len(history) == 4
        assert history[2].content == "¿Tenéis soporte?"

    def test_clear_session(self):
        self.store.add_turn("s3", "msg", "resp")
        self.store.clear_session("s3")
        assert self.store.get_history("s3") == []

    def test_history_trimmed_at_max_turns(self):
        from app.services.memory import MAX_HISTORY_TURNS
        for i in range(MAX_HISTORY_TURNS + 5):
            self.store.add_turn("s4", f"user {i}", f"bot {i}")
        history = self.store.get_history("s4")
        assert len(history) <= MAX_HISTORY_TURNS * 2

    def test_get_summary_format(self):
        self.store.add_turn("s5", "Pregunta", "Respuesta")
        summary = self.store.get_summary("s5")
        assert "Usuario" in summary
        assert "Asistente" in summary
        assert "Pregunta" in summary

    def test_active_sessions_count(self):
        initial = self.store.active_sessions
        self.store.add_turn("new_session", "test", "test")
        assert self.store.active_sessions == initial + 1


# ── Company Config Tests ───────────────────────────────────────────────────────

class TestCompanyConfig:
    def setup_method(self, tmp_path=None):
        # Patch CONFIG_FILE so tests don't write to disk
        import app.services.company_config as cc_module
        self._original = cc_module.CONFIG_FILE
        cc_module.CONFIG_FILE = Path("/tmp/test_company_configs.json")
        from app.services.company_config import CompanyConfigStore
        self.store = CompanyConfigStore()

    def teardown_method(self):
        import app.services.company_config as cc_module
        cc_module.CONFIG_FILE = self._original
        Path("/tmp/test_company_configs.json").unlink(missing_ok=True)

    def test_get_missing_returns_default(self):
        cfg = self.store.get("does_not_exist")
        assert cfg.company_id == "does_not_exist"

    def test_set_and_get(self):
        from app.models.schemas import CompanyConfig
        cfg = CompanyConfig(
            company_id="acme",
            company_name="ACME Corp",
            bot_name="Max",
        )
        self.store.set(cfg)
        retrieved = self.store.get("acme")
        assert retrieved.company_name == "ACME Corp"
        assert retrieved.bot_name == "Max"

    def test_overwrite_existing(self):
        from app.models.schemas import CompanyConfig
        self.store.set(CompanyConfig(company_id="x", bot_name="V1"))
        self.store.set(CompanyConfig(company_id="x", bot_name="V2"))
        assert self.store.get("x").bot_name == "V2"

    def test_delete_existing(self):
        from app.models.schemas import CompanyConfig
        self.store.set(CompanyConfig(company_id="del_me"))
        deleted = self.store.delete("del_me")
        assert deleted is True
        assert self.store.get("del_me").company_id == "del_me"  # returns default

    def test_delete_missing_returns_false(self):
        assert self.store.delete("ghost") is False

    def test_list_all(self):
        from app.models.schemas import CompanyConfig
        self.store.set(CompanyConfig(company_id="a"))
        self.store.set(CompanyConfig(company_id="b"))
        all_cfgs = self.store.list_all()
        ids = [c.company_id for c in all_cfgs]
        assert "a" in ids and "b" in ids


# ── Ingestion Tests ────────────────────────────────────────────────────────────

class TestIngestion:
    @pytest.mark.asyncio
    async def test_ingest_markdown_file(self, sample_md_file):
        mock_store = MagicMock()
        mock_store.add_documents.return_value = 3

        with patch("app.services.ingestion.get_vector_store", return_value=mock_store):
            from app.services.ingestion import ingest_files
            chunks, processed = await ingest_files([sample_md_file], company_id="test")

        assert chunks > 0
        assert "test_doc.md" in processed
        mock_store.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_txt_file(self, sample_txt_file):
        mock_store = MagicMock()
        mock_store.add_documents.return_value = 2

        with patch("app.services.ingestion.get_vector_store", return_value=mock_store):
            from app.services.ingestion import ingest_files
            chunks, processed = await ingest_files([sample_txt_file], company_id="test")

        assert "faq.txt" in processed

    @pytest.mark.asyncio
    async def test_unsupported_extension_skipped(self, tmp_path):
        bad_file = tmp_path / "data.csv"
        bad_file.write_text("col1,col2\n1,2")

        mock_store = MagicMock()
        with patch("app.services.ingestion.get_vector_store", return_value=mock_store):
            from app.services.ingestion import ingest_files
            with pytest.raises(ValueError, match="No se pudo procesar"):
                await ingest_files([bad_file], company_id="test")

    @pytest.mark.asyncio
    async def test_ingest_text_directly(self):
        mock_store = MagicMock()
        mock_store.add_documents.return_value = 1

        with patch("app.services.ingestion.get_vector_store", return_value=mock_store):
            from app.services.ingestion import ingest_text
            count = await ingest_text("Hola mundo. Este es un texto de prueba.", "test.txt", "test")

        assert count >= 0
        mock_store.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_multiple_files(self, sample_md_file, sample_txt_file):
        mock_store = MagicMock()
        mock_store.add_documents.return_value = 5

        with patch("app.services.ingestion.get_vector_store", return_value=mock_store):
            from app.services.ingestion import ingest_files
            chunks, processed = await ingest_files(
                [sample_md_file, sample_txt_file], company_id="multi"
            )

        assert len(processed) == 2


# ── Chat Engine Tests (mocked) ─────────────────────────────────────────────────

class TestChatEngine:
    @pytest.mark.asyncio
    async def test_escalation_detected(self):
        from app.services.chat_engine import chat

        mock_store = MagicMock()
        mock_store.similarity_search_with_score.return_value = []

        with patch("app.services.chat_engine.get_vector_store", return_value=mock_store), \
             patch("app.services.chat_engine.config_store") as mock_cfg:

            from app.models.schemas import CompanyConfig
            mock_cfg.get.return_value = CompanyConfig(
                company_id="default",
                escalation_keywords=["hablar con agente", "agente humano"],
            )

            result = await chat("sess_esc", "quiero hablar con agente", "default")

        assert result.fallback is True
        assert result.fallback_reason == "escalation"

    @pytest.mark.asyncio
    async def test_no_context_triggers_fallback(self):
        from app.services.chat_engine import chat
        from app.models.schemas import CompanyConfig

        mock_store = MagicMock()
        # Score below threshold → no context
        mock_store.similarity_search_with_score.return_value = [
            (MagicMock(page_content="irrelevante", metadata={}), 0.1)
        ]

        with patch("app.services.chat_engine.get_vector_store", return_value=mock_store), \
             patch("app.services.chat_engine.config_store") as mock_cfg:

            mock_cfg.get.return_value = CompanyConfig(company_id="default")
            result = await chat("sess_nocontext", "¿Cuál es la receta de paella?", "default")

        assert result.fallback is True
        assert result.fallback_reason == "no_context"

    @pytest.mark.asyncio
    async def test_successful_rag_response(self):
        from app.services.chat_engine import chat
        from app.models.schemas import CompanyConfig
        from langchain_core.documents import Document

        mock_doc = Document(
            page_content="El plan básico cuesta 20€ al mes.",
            metadata={"source_file": "manual.md", "page": 0},
        )
        mock_store = MagicMock()
        mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.85)]

        mock_llm_response = MagicMock()
        mock_llm_response.content = "El plan básico tiene un coste de 20€ mensuales."

        with patch("app.services.chat_engine.get_vector_store", return_value=mock_store), \
             patch("app.services.chat_engine.config_store") as mock_cfg, \
             patch("app.services.chat_engine.get_llm") as mock_get_llm:

            mock_cfg.get.return_value = CompanyConfig(company_id="default")
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm

            result = await chat("sess_ok", "¿Cuánto cuesta el plan básico?", "default")

        assert result.fallback is False
        assert "20€" in result.answer
        assert len(result.sources) == 1
        assert result.sources[0].file == "manual.md"

    @pytest.mark.asyncio
    async def test_history_passed_to_llm(self):
        """Verifica que el historial de sesión se incluye en la llamada al LLM."""
        from app.services.chat_engine import chat
        from app.services.memory import session_store
        from app.models.schemas import CompanyConfig
        from langchain_core.documents import Document

        session_id = "sess_history_test"
        session_store.add_turn(session_id, "Primera pregunta", "Primera respuesta del bot")

        mock_doc = Document(
            page_content="Información relevante aquí.",
            metadata={"source_file": "doc.md"},
        )
        mock_store = MagicMock()
        mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.9)]

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Respuesta con contexto."

        with patch("app.services.chat_engine.get_vector_store", return_value=mock_store), \
             patch("app.services.chat_engine.config_store") as mock_cfg, \
             patch("app.services.chat_engine.get_llm") as mock_get_llm:

            mock_cfg.get.return_value = CompanyConfig(company_id="default")
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm

            await chat(session_id, "Segunda pregunta", "default")

            # The messages passed to ainvoke should include history
            call_args = mock_llm.ainvoke.call_args[0][0]
            contents = [m.content for m in call_args]
            assert any("Primera pregunta" in c for c in contents)

        session_store.clear_session(session_id)


# ── API Endpoint Tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    # Patch settings so no real API key is needed
    with patch("app.core.config.Settings.anthropic_api_key", new_callable=lambda: property(lambda self: "sk-ant-test")):
        from main import app
        with TestClient(app) as c:
            yield c


class TestAPIEndpoints:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert data["name"] == "SmartChat API"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "vector_store" in data

    def test_get_config_default(self, client):
        r = client.get("/api/v1/config/default")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "config" in data

    def test_create_config(self, client):
        payload = {
            "company_id": "test_co",
            "company_name": "Test Company",
            "bot_name": "TestBot",
            "industry": "saas",
            "system_role": "Eres un asistente de {company_name}.",
            "fallback_message": "No tengo esa info.",
            "handoff_message": "Te paso con un agente.",
            "escalation_keywords": ["agente", "humano"],
        }
        r = client.post("/api/v1/config", json=payload)
        assert r.status_code == 200
        assert r.json()["config"]["company_name"] == "Test Company"

    def test_list_configs(self, client):
        r = client.get("/api/v1/config")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_chat_endpoint_requires_fields(self, client):
        r = client.post("/api/v1/chat", json={})
        assert r.status_code == 422  # Validation error

    def test_clear_session(self, client):
        r = client.delete("/api/v1/chat/session/test_session_123")
        assert r.status_code == 200
        assert r.json()["session_id"] == "test_session_123"

    def test_document_count_endpoint(self, client):
        r = client.get("/api/v1/documents/count/default")
        assert r.status_code == 200
        assert "chunks" in r.json()

    def test_upload_unsupported_file_type(self, client, tmp_path):
        bad_file = tmp_path / "data.csv"
        bad_file.write_text("a,b,c\n1,2,3")
        with open(bad_file, "rb") as f:
            r = client.post(
                "/api/v1/documents/upload",
                files=[("files", ("data.csv", f, "text/csv"))],
                data={"company_id": "default"},
            )
        assert r.status_code == 400
        assert "no soportado" in r.json()["detail"].lower()
