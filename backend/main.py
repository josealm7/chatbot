"""
SmartChat Backend — FastAPI + LangChain + Claude
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import get_settings
from app.api import chat, documents, config, health

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  SmartChat API arrancando...")
    logger.info(f"  Vector store  : {settings.vector_store}")
    logger.info(f"  Model         : {settings.model_name}")
    logger.info(f"  Environment   : {settings.app_env}")
    logger.info("=" * 60)

    # Asegurar directorios necesarios
    Path("./data/chroma_db").mkdir(parents=True, exist_ok=True)
    Path("./data/uploads").mkdir(parents=True, exist_ok=True)

    yield

    logger.info("SmartChat API apagándose...")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SmartChat API",
    description="Backend RAG para chatbot empresarial con LangChain + Claude",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")

# ── Static (frontend) ─────────────────────────────────────────────────────────
frontend_dir = Path("../frontend")
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info("Frontend montado en /app")
