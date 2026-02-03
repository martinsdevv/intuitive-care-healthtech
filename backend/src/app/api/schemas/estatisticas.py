from typing import Dict, List

from pydantic import BaseModel


class TopOperadora(BaseModel):
    cnpj: str | None
    razao_social: str | None
    total_despesas: float


class EstatisticasResponse(BaseModel):
    total_despesas: float
    media_despesas: float
    top5_operadoras: List[TopOperadora]
    despesas_por_uf: Dict[str, float]
