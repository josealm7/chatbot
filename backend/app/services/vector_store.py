"""
Vector Store Service
Abstracción sobre ChromaDB (local, sin cuenta) y Pinecone (cloud).
Por defecto usa ChromaDB para facilitar el desarrollo.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Embeddings ────────────────────────────────────────────────────────────────
# Usamos un modelo ligero local (no necesita API key)
# all-MiniLM-L6-v2 → 384 dims, ~80 MB, excelente para español + inglés

def get_embeddings() -> Embeddings:
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ── ChromaDB ──────────────────────────────────────────────────────────────────

class ChromaVectorStore:
    def __init__(self, company_id: str = "default"):
        self.company_id = company_id
        self.collection_name = f"smartchat_{company_id}"
        self._store = None

    def _get_store(self):
        if self._store is None:
            from langchain_community.vectorstores import Chroma
            persist_dir = Path(settings.chroma_persist_dir) / self.company_id
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._store = Chroma(
                collection_name=self.collection_name,
                embedding_function=get_embeddings(),
                persist_directory=str(persist_dir),
            )
        return self._store

    def add_documents(self, docs: list[Document]) -> int:
        store = self._get_store()
        store.add_documents(docs)
        return len(docs)

    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> list[tuple[Document, float]]:
        store = self._get_store()
        return store.similarity_search_with_relevance_scores(query, k=k)

    def delete_collection(self) -> None:
        store = self._get_store()
        store.delete_collection()
        self._store = None
        logger.info(f"Colección '{self.collection_name}' eliminada")

    def count(self) -> int:
        try:
            store = self._get_store()
            return store._collection.count()
        except Exception:
            return 0


# ── Pinecone ──────────────────────────────────────────────────────────────────

class PineconeVectorStore:
    def __init__(self, company_id: str = "default"):
        self.company_id = company_id
        self.namespace = f"company_{company_id}"
        self._store = None

    def _get_store(self):
        if self._store is None:
            from pinecone import Pinecone
            from langchain_community.vectorstores import Pinecone as LCPinecone

            pc = Pinecone(api_key=settings.pinecone_api_key)
            index = pc.Index(settings.pinecone_index_name)
            self._store = LCPinecone(
                index=index,
                embedding=get_embeddings(),
                text_key="text",
                namespace=self.namespace,
            )
        return self._store

    def add_documents(self, docs: list[Document]) -> int:
        store = self._get_store()
        store.add_documents(docs)
        return len(docs)

    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> list[tuple[Document, float]]:
        store = self._get_store()
        return store.similarity_search_with_score(query, k=k)

    def delete_collection(self) -> None:
        # Pinecone: eliminamos el namespace
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        index.delete(delete_all=True, namespace=self.namespace)
        self._store = None

    def count(self) -> int:
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.pinecone_api_key)
            index = pc.Index(settings.pinecone_index_name)
            stats = index.describe_index_stats()
            ns = stats.namespaces.get(self.namespace)
            return ns.vector_count if ns else 0
        except Exception:
            return 0


# ── Factory ───────────────────────────────────────────────────────────────────

_store_cache: dict[str, ChromaVectorStore | PineconeVectorStore] = {}


def get_vector_store(company_id: str = "default"):
    if company_id not in _store_cache:
        if settings.vector_store == "pinecone":
            if not settings.pinecone_api_key:
                raise ValueError("PINECONE_API_KEY no configurada. Usa VECTOR_STORE=chroma para desarrollo local.")
            _store_cache[company_id] = PineconeVectorStore(company_id)
            logger.info(f"Vector store: Pinecone | namespace={company_id}")
        else:
            _store_cache[company_id] = ChromaVectorStore(company_id)
            logger.info(f"Vector store: ChromaDB local | company={company_id}")
    return _store_cache[company_id]


def clear_store_cache(company_id: str):
    _store_cache.pop(company_id, None)
