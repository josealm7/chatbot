# 🤖 SmartChat — Chatbot RAG para Empresas

> Chatbot empresarial con IA que responde usando **documentos reales** de tu empresa, mantiene **contexto de conversación** y escala a agentes humanos cuando es necesario.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C)
![Claude](https://img.shields.io/badge/Claude-Anthropic-7c6af7)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-32%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## ✨ Funcionalidades

| Característica | Descripción |
|---|---|
| 📄 **RAG con documentos reales** | Indexa PDF, TXT y Markdown. El bot responde usando esa info |
| 🧠 **Memoria de conversación** | Recuerda el historial de cada sesión (configurable) |
| 🎭 **Sistema de roles** | Define el rol del bot por empresa: seguros, SaaS, legal… |
| 🚨 **Fallback inteligente** | Sin contexto → avisa; pide agente → escala automáticamente |
| 🔌 **Multi-empresa** | Un backend, múltiples bots con configs independientes |
| 🗄️ **Vector store flexible** | ChromaDB local (sin cuenta) o Pinecone cloud |
| 🐳 **Docker listo** | `docker compose up` y funciona |
| ✅ **Tests incluidos** | 32 tests con pytest cubriendo servicios y endpoints |

---

## 🏗️ Arquitectura

```
Usuario → Frontend (HTML/JS)
              ↓ fetch /api/v1/chat
         FastAPI Backend
              ↓
    ┌─────────────────────┐
    │    Chat Engine      │  ← LangChain + Claude (Anthropic)
    │  1. Detectar escal. │
    │  2. Retrieve docs   │  ← ChromaDB / Pinecone
    │  3. Score confianza │
    │  4. Build prompt    │  ← System role + historial + contexto
    │  5. Llamar al LLM   │
    │  6. Devolver +fuentes│
    └─────────────────────┘
              ↓
    SessionMemory (historial por sesión)
    CompanyConfig (roles por empresa)
```

---

## 🚀 Inicio rápido

### Opción A — Sin Docker (desarrollo)

```bash
# 1. Clonar y entrar
git clone https://github.com/tuusuario/smartchat.git
cd smartchat/backend

# 2. Entorno virtual
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar entorno
cp .env.example .env
# Edita .env y añade tu ANTHROPIC_API_KEY

# 5. Arrancar
uvicorn main:app --reload --port 8000
```

Abre `frontend/index.html` en el navegador. API docs en `http://localhost:8000/docs`.

---

### Opción B — Docker (recomendado)

```bash
# 1. Clonar
git clone https://github.com/tuusuario/smartchat.git
cd smartchat

# 2. Configurar API key
cp backend/.env.example backend/.env
# Edita backend/.env con tu ANTHROPIC_API_KEY

# 3. Levantar todo
docker compose up --build
```

| Servicio | URL |
|---|---|
| Frontend (chat) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

El servicio `seed` carga automáticamente el documento de ejemplo (`segurmax_manual.md`) al arrancar.

---

## ⚙️ Configuración

Copia `backend/.env.example` a `backend/.env` y configura:

```env
# Requerido
ANTHROPIC_API_KEY=sk-ant-...

# Vector store: "chroma" (local, sin cuenta) | "pinecone" (cloud)
VECTOR_STORE=chroma

# Solo si usas Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=smartchat-docs
```

---

## 🎭 Configurar el bot para tu empresa

Vía API o desde el panel del frontend:

```bash
curl -X POST http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "miempresa",
    "company_name": "Mi Empresa S.L.",
    "bot_name": "Sofía",
    "system_role": "Eres Sofía, asistente de {company_name}. Responde en español, de forma profesional.",
    "fallback_message": "No tengo esa información. ¿Te pongo con un agente?",
    "escalation_keywords": ["agente", "humano", "queja", "reclamación"]
  }'
```

---

## 📄 Subir documentos

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "company_id=miempresa" \
  -F "files=@manual_producto.pdf" \
  -F "files=@faq.md"
```

Formatos soportados: **PDF**, **TXT**, **Markdown** (máx. 20 MB por archivo).

---

## 🧪 Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

```
tests/test_all.py::TestSchemas::test_chat_request_valid          PASSED
tests/test_all.py::TestSchemas::test_company_config_defaults     PASSED
tests/test_all.py::TestSessionMemory::test_add_turn_and_retrieve PASSED
tests/test_all.py::TestChatEngine::test_escalation_detected      PASSED
tests/test_all.py::TestChatEngine::test_successful_rag_response  PASSED
tests/test_all.py::TestAPIEndpoints::test_health                 PASSED
... 32 tests en total
```

---

## 📡 Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/chat` | Enviar mensaje al bot |
| `DELETE` | `/api/v1/chat/session/{id}` | Limpiar historial de sesión |
| `POST` | `/api/v1/documents/upload` | Subir documentos |
| `GET` | `/api/v1/documents/count/{company_id}` | Chunks indexados |
| `DELETE` | `/api/v1/documents/{company_id}` | Eliminar todos los docs |
| `POST` | `/api/v1/config` | Crear/actualizar config de empresa |
| `GET` | `/api/v1/config/{company_id}` | Obtener config |
| `GET` | `/health` | Estado del sistema |

---

## 🛠️ Stack técnico

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — API REST async
- [LangChain](https://python.langchain.com/) — orquestación RAG
- [Anthropic Claude](https://anthropic.com/) — LLM (claude-haiku-4-5)
- [ChromaDB](https://www.trychroma.com/) — vector store local
- [Pinecone](https://www.pinecone.io/) — vector store cloud (opcional)
- [HuggingFace Embeddings](https://huggingface.co/) — `all-MiniLM-L6-v2`
- [PyPDF](https://pypdf.readthedocs.io/) — parsing de PDFs
- [Pydantic v2](https://docs.pydantic.dev/) — validación de datos
- [pytest](https://pytest.org/) — testing

**Frontend**
- HTML + JavaScript vanilla (sin frameworks)
- nginx — servidor estático + reverse proxy

**Infraestructura**
- Docker + docker-compose
- GitHub Actions ready

---

## 📁 Estructura del proyecto

```
smartchat/
├── docker-compose.yml
├── start.sh
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── .env.example
│   ├── app/
│   │   ├── api/                   # Endpoints REST
│   │   ├── core/                  # Config / settings
│   │   ├── models/                # Schemas Pydantic
│   │   └── services/              # Lógica de negocio
│   │       ├── chat_engine.py     # RAG + Claude
│   │       ├── vector_store.py    # ChromaDB / Pinecone
│   │       ├── ingestion.py       # Carga de documentos
│   │       ├── memory.py          # Historial de sesión
│   │       └── company_config.py  # Config por empresa
│   ├── scripts/seed.py            # Carga docs de ejemplo
│   ├── tests/test_all.py          # 32 tests
│   └── data/documents/            # Tus documentos aquí
└── frontend/
    ├── index.html                 # Chat UI
    ├── Dockerfile
    └── nginx.conf
```

---

## 📄 Licencia

MIT — libre para uso comercial y personal.

---

*Desarrollado como demostración de integración de chatbots IA en entornos empresariales. Stack: FastAPI · LangChain · Claude · ChromaDB · Docker.*
