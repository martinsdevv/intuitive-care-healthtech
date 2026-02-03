from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class OperadoraOut(BaseModel):
    registro_ans: int
    cnpj: Optional[str]
    razao_social: Optional[str]
    nome_fantasia: Optional[str]
    modalidade: Optional[str]
    uf: Optional[str]
    cidade: Optional[str]
    logradouro: Optional[str]
    numero: Optional[str]
    complemento: Optional[str]
    bairro: Optional[str]
    cep: Optional[str]
    ddd: Optional[str]
    telefone: Optional[str]
    fax: Optional[str]
    endereco_eletronico: Optional[str]
    representante: Optional[str]
    cargo_representante: Optional[str]
    regiao_comercializacao: Optional[str]
    data_registro_ans: Optional[date]


class OperadoraListResponse(BaseModel):
    data: List[OperadoraOut]
    total: int
    page: int
    limit: int


class DespesaItem(BaseModel):
    ano: int
    trimestre: int
    valor: float


class DespesasResponse(BaseModel):
    cnpj: str
    items: List[DespesaItem]
