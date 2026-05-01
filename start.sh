#!/bin/bash
# ── SmartChat — Script de inicio rápido ─────────────────────────────────────
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"
VENV_DIR="$BACKEND_DIR/.venv"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║        SmartChat — Backend RAG       ║"
echo "  ║   LangChain + Claude + ChromaDB      ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# 1. Verificar Python
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Python 3 no encontrado. Instala Python 3.11+${NC}"
  exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓ Python ${PYTHON_VER}${NC}"

# 2. Crear .env si no existe
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo -e "${YELLOW}⚠ Creado .env desde .env.example${NC}"
  echo -e "${YELLOW}  → Edita backend/.env y añade tu ANTHROPIC_API_KEY${NC}"
  echo ""
fi

# 3. Verificar API key
if ! grep -q "^ANTHROPIC_API_KEY=sk-ant-" "$BACKEND_DIR/.env" 2>/dev/null; then
  echo -e "${RED}✗ ANTHROPIC_API_KEY no configurada en backend/.env${NC}"
  echo -e "  Edita el archivo y añade: ANTHROPIC_API_KEY=sk-ant-tu-key"
  exit 1
fi

echo -e "${GREEN}✓ API key detectada${NC}"

# 4. Crear/activar virtualenv
if [ ! -d "$VENV_DIR" ]; then
  echo -e "${BLUE}→ Creando entorno virtual...${NC}"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 5. Instalar dependencias
echo -e "${BLUE}→ Instalando dependencias (puede tardar en la primera vez)...${NC}"
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# 6. Crear directorios necesarios
mkdir -p "$BACKEND_DIR/data/chroma_db" "$BACKEND_DIR/data/uploads"

# 7. Arrancar backend
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Backend: http://localhost:8000${NC}"
echo -e "${GREEN}  API docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}  Frontend: abre frontend/index.html en el navegador${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$BACKEND_DIR"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
