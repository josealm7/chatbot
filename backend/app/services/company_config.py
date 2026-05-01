"""
Company Config Store
Gestiona las configuraciones de las empresas/bots.
Persistencia simple en JSON (producción: base de datos).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.schemas import CompanyConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("./data/company_configs.json")


class CompanyConfigStore:
    def __init__(self):
        self._configs: dict[str, CompanyConfig] = {}
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for cid, data in raw.items():
                    self._configs[cid] = CompanyConfig(**data)
                logger.info(f"Loaded {len(self._configs)} company configs")
            except Exception as e:
                logger.warning(f"Could not load configs: {e}")

    def _save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: cfg.model_dump() for cid, cfg in self._configs.items()}
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, company_id: str) -> CompanyConfig:
        return self._configs.get(company_id, CompanyConfig(company_id=company_id))

    def set(self, config: CompanyConfig) -> None:
        self._configs[config.company_id] = config
        self._save()

    def delete(self, company_id: str) -> bool:
        if company_id in self._configs:
            del self._configs[company_id]
            self._save()
            return True
        return False

    def list_all(self) -> list[CompanyConfig]:
        return list(self._configs.values())


# Singleton global
config_store = CompanyConfigStore()
