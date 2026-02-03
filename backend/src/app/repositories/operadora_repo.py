from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class OperadoraRepository:
    def count_operadoras(self, db: Session, q_text: str, q_digits: str) -> int:
        sql = text(
            """
            SELECT COUNT(*)
            FROM healthtech.operadora
            WHERE (
              :q_text = ''
              OR razao_social ILIKE :q_like
              OR (:q_digits <> '' AND cnpj LIKE :cnpj_like)
            )
            """
        )
        params = {
            "q_text": q_text,  # sempre string
            "q_like": f"%{q_text}%",  # "%%" quando vazio
            "q_digits": q_digits,  # sempre string
            "cnpj_like": f"%{q_digits}%",  # "%%" quando vazio
        }
        return int(db.execute(sql, params).scalar_one())

    def list_operadoras(
        self, db: Session, page: int, limit: int, q_text: str, q_digits: str
    ):
        offset = (page - 1) * limit
        sql = text(
            """
            SELECT
              registro_ans, cnpj, razao_social, nome_fantasia, modalidade, uf,
              cidade, logradouro, numero, complemento, bairro, cep, ddd, telefone, fax,
              endereco_eletronico, representante, cargo_representante, regiao_comercializacao,
              data_registro_ans
            FROM healthtech.operadora
            WHERE (
              :q_text = ''
              OR razao_social ILIKE :q_like
              OR (:q_digits <> '' AND cnpj LIKE :cnpj_like)
            )
            ORDER BY razao_social NULLS LAST, registro_ans
            LIMIT :limit OFFSET :offset
            """
        )
        params = {
            "q_text": q_text,
            "q_like": f"%{q_text}%",
            "q_digits": q_digits,
            "cnpj_like": f"%{q_digits}%",
            "limit": limit,
            "offset": offset,
        }
        return db.execute(sql, params).mappings().all()

    def get_operadora_by_cnpj(self, db: Session, cnpj: str):
        sql = text(
            """
            SELECT
              registro_ans, cnpj, razao_social, nome_fantasia, modalidade, uf,
              cidade, logradouro, numero, complemento, bairro, cep, ddd, telefone, fax,
              endereco_eletronico, representante, cargo_representante, regiao_comercializacao,
              data_registro_ans
            FROM healthtech.operadora
            WHERE cnpj = :cnpj
            LIMIT 1
            """
        )
        return db.execute(sql, {"cnpj": cnpj}).mappings().first()

    def get_registro_ans_by_cnpj(self, db: Session, cnpj: str) -> int | None:
        sql = text(
            "SELECT registro_ans FROM healthtech.operadora WHERE cnpj = :cnpj LIMIT 1"
        )
        v = db.execute(sql, {"cnpj": cnpj}).scalar()
        return int(v) if v is not None else None

    def list_despesas_by_registro(self, db: Session, registro_ans: int):
        sql = text(
            """
            SELECT ano, trimestre, valor_despesas
            FROM healthtech.despesa_trimestral
            WHERE registro_ans = :registro_ans
            ORDER BY ano ASC, trimestre ASC
            """
        )
        return db.execute(sql, {"registro_ans": registro_ans}).all()
