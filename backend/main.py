"""
SmartChat Backend — FastAPI + LangChain + Groq
Security: rate limiting · strict CORS · sanitized errors
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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

# ── Rate Limiter ──────────────────────────────────────────────────────────────
# 30 peticiones por minuto por IP — suficiente para uso normal
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  SmartChat API arrancando...")
    logger.info(f"  Vector store  : {settings.vector_store}")
    logger.info(f"  Model         : {settings.model_name}")
    logger.info(f"  Environment   : {settings.app_env}")
    logger.info("=" * 60)
    Path("./data/chroma_db").mkdir(parents=True, exist_ok=True)
    Path("./data/uploads").mkdir(parents=True, exist_ok=True)
    yield
    logger.info("SmartChat API apagándose...")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SmartChat API",
    description="Backend RAG para chatbot empresarial con LangChain + Groq",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# ── Rate limiting middleware ──────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS estricto ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# ── Error handler — no exponer stack traces en producción ─────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    if settings.app_env == "development":
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Por favor, inténtalo de nuevo."}
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