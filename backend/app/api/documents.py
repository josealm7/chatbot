import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.schemas import IngestResponse, DeleteDocumentsResponse
from app.services.ingestion import ingest_files, ingest_text, delete_all_documents
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20
DEFAULT_DOC = Path("./data/documents/segurmax_manual.md")


@router.post("/upload", response_model=IngestResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    company_id: str = Form(default="default"),
):
    if not files:
        raise HTTPException(status_code=400, detail="No se enviaron archivos.")
    saved_paths: list[Path] = []
    company_upload_dir = UPLOAD_DIR / company_id
    company_upload_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400,
                detail=f"Tipo no soportado: {file.filename}. Solo PDF, TXT y MD.")
        content = await file.read()
        if len(content) / (1024 * 1024) > MAX_FILE_SIZE_MB:
            raise HTTPException(status_code=400,
                detail=f"{file.filename} supera {MAX_FILE_SIZE_MB}MB.")
        dest = company_upload_dir / file.filename
        dest.write_bytes(content)
        saved_paths.append(dest)
    try:
        chunks, processed = await ingest_files(saved_paths, company_id=company_id)
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar documentos: {str(e)}")
    return IngestResponse(status="ok", chunks_indexed=chunks,
                          files_processed=processed, company_id=company_id)


@router.post("/load-default", response_model=IngestResponse)
async def load_default_document(company_id: str = Form(default="default")):
    if not DEFAULT_DOC.exists():
        raise HTTPException(status_code=404, detail="Documento predeterminado no encontrado.")
    try:
        chunks, processed = await ingest_files([DEFAULT_DOC], company_id=company_id)
        return IngestResponse(status="ok", chunks_indexed=chunks,
                              files_processed=processed, company_id=company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default-doc")
async def get_default_document():
    if not DEFAULT_DOC.exists():
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return {"filename": DEFAULT_DOC.name, "content": DEFAULT_DOC.read_text(encoding="utf-8")}


@router.get("/count/{company_id}")
async def get_document_count(company_id: str = "default"):
    store = get_vector_store(company_id)
    return {"company_id": company_id, "chunks": store.count()}


@router.post("/ingest-text", response_model=IngestResponse)
async def ingest_text_endpoint(
    text: str = Form(...),
    filename: str = Form(default="manual.txt"),
    company_id: str = Form(default="default"),
):
    try:
        chunks = await ingest_text(text, filename=filename, company_id=company_id)
        return IngestResponse(status="ok", chunks_indexed=chunks,
                              files_processed=[filename], company_id=company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{company_id}", response_model=DeleteDocumentsResponse)
async def delete_documents(company_id: str):
    try:
        await delete_all_documents(company_id)
        company_upload_dir = UPLOAD_DIR / company_id
        if company_upload_dir.exists():
            shutil.rmtree(company_upload_dir)
        return DeleteDocumentsResponse(status="ok", company_id=company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))