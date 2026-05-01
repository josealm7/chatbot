"""
Document Ingestion Service
Carga documentos (PDF, TXT, MD), los divide en chunks y los indexa.
"""
from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.services.vector_store import get_vector_store, clear_store_cache

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def _load_document(file_path: Path) -> list[Document]:
    """Carga un documento según su extensión."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()
    elif ext in (".txt", ".md"):
        content = file_path.read_text(encoding="utf-8")
        docs = [Document(
            page_content=content,
            metadata={"source_file": file_path.name, "file_type": ext}
        )]
    else:
        raise ValueError(f"Tipo de archivo no soportado: {ext}")

    for doc in docs:
        doc.metadata["source_file"] = file_path.name
        doc.metadata["file_type"] = ext
    return docs


def _split_documents(docs: list[Document]) -> list[Document]:
    """Divide documentos en chunks con overlap."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Split: {len(docs)} docs → {len(chunks)} chunks")
    return chunks


async def ingest_files(
    file_paths: list[Path],
    company_id: str = "default",
) -> tuple[int, list[str]]:
    all_chunks: list[Document] = []
    processed: list[str] = []
    errors: list[str] = []

    for path in file_paths:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file: {path.name}")
            continue
        try:
            docs = _load_document(path)
            chunks = _split_documents(docs)
            all_chunks.extend(chunks)
            processed.append(path.name)
            logger.info(f"Loaded: {path.name} → {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Error loading {path.name}: {e}")
            errors.append(path.name)

    if not all_chunks:
        raise ValueError("No se pudo procesar ningún documento válido.")

    store = get_vector_store(company_id)
    indexed = store.add_documents(all_chunks)
    logger.info(f"Indexed {indexed} chunks for company '{company_id}'")

    return indexed, processed


async def ingest_text(
    text: str,
    filename: str,
    company_id: str = "default",
) -> int:
    doc = Document(
        page_content=text,
        metadata={"source_file": filename, "file_type": "text/plain"},
    )
    chunks = _split_documents([doc])
    store = get_vector_store(company_id)
    return store.add_documents(chunks)


async def delete_all_documents(company_id: str = "default") -> None:
    store = get_vector_store(company_id)
    store.delete_collection()
    clear_store_cache(company_id)
    logger.info(f"Deleted all docs for company '{company_id}'")