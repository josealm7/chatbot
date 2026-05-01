"""
Seed Script
Carga documentos de ejemplo y configura una empresa demo al arrancar.
Se ejecuta una sola vez via docker-compose (servicio 'seed').
También se puede correr manualmente:
    python scripts/seed.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_BASE = "http://backend:8000"   # inside Docker
LOCAL_API = "http://localhost:8000"  # local dev fallback
DOCS_DIR = Path(__file__).parent.parent / "data" / "documents"

DEMO_COMPANY = {
    "company_id": "default",
    "company_name": "SegurMax S.L.",
    "bot_name": "Sofía",
    "industry": "seguros",
    "system_role": (
        "Eres Sofía, la asistente virtual de SegurMax S.L., una compañía de seguros española. "
        "Tu objetivo es ayudar a los clientes con información sobre pólizas, siniestros, precios y contratación. "
        "Responde siempre en español, de forma amable y profesional. "
        "Si el cliente muestra frustración, muestra empatía antes de responder. "
        "No inventes información que no esté en los documentos."
    ),
    "fallback_message": (
        "Lo siento, no tengo información específica sobre eso en este momento. "
        "¿Te gustaría que te pusiera en contacto con uno de nuestros agentes? "
        "Están disponibles de lunes a viernes de 9:00 a 19:00 en el 900 123 456."
    ),
    "handoff_message": (
        "Entendido, voy a conectarte con uno de nuestros agentes especializados. "
        "Un momento por favor... 🙋 En breve alguien del equipo se pondrá en contacto contigo."
    ),
    "escalation_keywords": [
        "hablar con humano", "agente", "persona real",
        "representante", "queja", "reclamación", "no me ayudas",
        "quiero hablar con alguien"
    ],
}


def wait_for_backend(base: str, retries: int = 20, delay: float = 3.0) -> bool:
    print(f"⏳ Esperando al backend en {base}...")
    for i in range(retries):
        try:
            r = httpx.get(f"{base}/health", timeout=5)
            if r.status_code == 200:
                print(f"✓ Backend listo")
                return True
        except Exception:
            pass
        print(f"  Intento {i+1}/{retries}...")
        time.sleep(delay)
    return False


def resolve_base() -> str:
    """Try Docker URL first, fall back to localhost."""
    for base in [API_BASE, LOCAL_API]:
        try:
            httpx.get(f"{base}/health", timeout=3)
            return base
        except Exception:
            continue
    return LOCAL_API


async def seed():
    base = resolve_base()

    if not wait_for_backend(base):
        print("✗ Backend no disponible. Abortando seed.")
        sys.exit(1)

    # 1. Configure demo company
    print("\n→ Configurando empresa demo...")
    r = httpx.post(f"{base}/api/v1/config", json=DEMO_COMPANY, timeout=15)
    if r.status_code == 200:
        print(f"  ✓ Empresa '{DEMO_COMPANY['company_name']}' configurada")
    else:
        print(f"  ⚠ Config error: {r.text}")

    # 2. Check if already indexed
    r = httpx.get(f"{base}/api/v1/documents/count/default", timeout=10)
    if r.status_code == 200:
        count = r.json().get("chunks", 0)
        if count > 0:
            print(f"\n✓ Documentos ya indexados ({count} chunks). Seed omitido.")
            return

    # 3. Upload sample documents
    doc_files = list(DOCS_DIR.glob("*"))
    if not doc_files:
        print("⚠ No hay documentos en data/documents/. Seed omitido.")
        return

    print(f"\n→ Indexando {len(doc_files)} documento(s)...")
    files_payload = []
    for doc_path in doc_files:
        files_payload.append(
            ("files", (doc_path.name, doc_path.read_bytes(), "text/plain"))
        )

    r = httpx.post(
        f"{base}/api/v1/documents/upload",
        files=files_payload,
        data={"company_id": "default"},
        timeout=120,
    )

    if r.status_code == 200:
        data = r.json()
        print(f"  ✓ {data['chunks_indexed']} chunks indexados")
        for f in data["files_processed"]:
            print(f"    📄 {f}")
    else:
        print(f"  ✗ Error al indexar: {r.text}")
        sys.exit(1)

    print("\n🚀 Seed completado. El chatbot está listo.")


if __name__ == "__main__":
    asyncio.run(seed())
