from __future__ import annotations

from app.api.utils import only_digits
from app.repositories.operadora_repo import OperadoraRepository
from fastapi import HTTPException
from sqlalchemy.orm import Session


class OperadoraService:
    def __init__(self, repo: OperadoraRepository):
        self.repo = repo

    def _normalize_q(self, q: str | None) -> tuple[str, str]:
        if not q:
            return "", ""
        q = q.strip()
        if not q:
            return "", ""
        q_digits = only_digits(q)
        return q, q_digits

    def _normalize_cnpj(self, cnpj: str) -> str:
        cnpj = only_digits(cnpj)
        if len(cnpj) != 14:
            raise HTTPException(status_code=422, detail="CNPJ deve conter 14 dígitos")
        return cnpj

    def listar(self, db: Session, page: int, limit: int, q: str | None):
        q_text, q_digits = self._normalize_q(q)
        total = self.repo.count_operadoras(db, q_text, q_digits)
        rows = self.repo.list_operadoras(db, page, limit, q_text, q_digits)
        return total, rows

    def detalhe(self, db: Session, cnpj: str):
        cnpj_norm = self._normalize_cnpj(cnpj)
        row = self.repo.get_operadora_by_cnpj(db, cnpj_norm)
        if not row:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        return row

    def despesas(self, db: Session, cnpj: str):
        cnpj_norm = self._normalize_cnpj(cnpj)
        reg = self.repo.get_registro_ans_by_cnpj(db, cnpj_norm)
        if reg is None:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        rows = self.repo.list_despesas_by_registro(db, reg)
        return cnpj_norm, rows
