from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class EstatisticasRepository:
    def total_despesas(self, db: Session):
        return db.execute(
            text(
                "SELECT COALESCE(SUM(valor_despesas), 0) FROM healthtech.despesa_trimestral"
            )
        ).scalar_one()

    def media_despesas(self, db: Session):
        return db.execute(
            text(
                "SELECT COALESCE(AVG(valor_despesas), 0) FROM healthtech.despesa_trimestral"
            )
        ).scalar_one()

    def top5_operadoras(self, db: Session):
        return (
            db.execute(
                text(
                    """
                SELECT o.cnpj, o.razao_social, COALESCE(SUM(d.valor_despesas), 0) AS total
                FROM healthtech.operadora o
                JOIN healthtech.despesa_trimestral d
                  ON d.registro_ans = o.registro_ans
                GROUP BY o.cnpj, o.razao_social
                ORDER BY total DESC
                LIMIT 5
                """
                )
            )
            .mappings()
            .all()
        )

    def despesas_por_uf(self, db: Session):
        return db.execute(
            text(
                """
                SELECT o.uf, COALESCE(SUM(d.valor_despesas), 0) AS total
                FROM healthtech.operadora o
                JOIN healthtech.despesa_trimestral d
                  ON d.registro_ans = o.registro_ans
                WHERE o.uf IS NOT NULL
                GROUP BY o.uf
                ORDER BY o.uf
                """
            )
        ).all()
