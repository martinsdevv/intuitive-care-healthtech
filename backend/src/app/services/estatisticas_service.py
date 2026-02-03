from __future__ import annotations

import os
import time

from app.repositories.estatisticas_repo import EstatisticasRepository
from sqlalchemy.orm import Session


class EstatisticasService:
    def __init__(self, repo: EstatisticasRepository):
        self.repo = repo
        self.ttl = int(os.getenv("STATS_CACHE_TTL", "300"))
        self._cache_value: dict | None = None
        self._cache_ts: float = 0.0

    def _cache_get(self) -> dict | None:
        if self._cache_value is None:
            return None
        if (time.monotonic() - self._cache_ts) > self.ttl:
            return None
        return self._cache_value

    def _cache_set(self, value: dict) -> None:
        self._cache_value = value
        self._cache_ts = time.monotonic()

    def get(self, db: Session) -> dict:
        cached = self._cache_get()
        if cached is not None:
            return cached

        total = self.repo.total_despesas(db)
        media = self.repo.media_despesas(db)
        top_rows = self.repo.top5_operadoras(db)
        uf_rows = self.repo.despesas_por_uf(db)

        payload = {
            "total_despesas": float(total or 0),
            "media_despesas": float(media or 0),
            "top5_operadoras": [
                {
                    "cnpj": r.get("cnpj"),
                    "razao_social": r.get("razao_social"),
                    "total_despesas": float(r.get("total") or 0),
                }
                for r in top_rows
            ],
            "despesas_por_uf": {
                str(uf): float(v) for (uf, v) in uf_rows if uf is not None
            },
        }

        self._cache_set(payload)
        return payload
