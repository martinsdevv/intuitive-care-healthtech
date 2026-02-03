from app.api.deps import get_db
from app.api.schemas.operadora import (
    DespesasResponse,
    OperadoraListResponse,
    OperadoraOut,
)
from app.repositories.operadora_repo import OperadoraRepository
from app.services.operadora_service import OperadoraService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter()
svc = OperadoraService(OperadoraRepository())


@router.get("", response_model=OperadoraListResponse)
def listar_operadoras(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    q: str | None = Query(
        None, description="Filtro por razão social ou CNPJ (parcial)"
    ),
    db: Session = Depends(get_db),
):
    total, rows = svc.listar(db, page, limit, q)
    return OperadoraListResponse(
        data=[OperadoraOut(**r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{cnpj}", response_model=OperadoraOut)
def obter_operadora(cnpj: str, db: Session = Depends(get_db)):
    row = svc.detalhe(db, cnpj)
    return OperadoraOut(**row)


@router.get("/{cnpj}/despesas", response_model=DespesasResponse)
def despesas_operadora(cnpj: str, db: Session = Depends(get_db)):
    cnpj_norm, rows = svc.despesas(db, cnpj)
    items = [
        {"ano": int(a), "trimestre": int(t), "valor": float(v)} for a, t, v in rows
    ]
    return DespesasResponse(cnpj=cnpj_norm, items=items)
