import csv
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple

from app.core.paths import OUTPUT_TESTE1_DIR, STAGING_DIR


def getArquivoStaging():
    return STAGING_DIR / "eventos_sinistros_staging.csv"


def getArquivoCsvFinal():
    return OUTPUT_TESTE1_DIR / "consolidado_despesas.csv"


def getArquivoZipFinal():
    return OUTPUT_TESTE1_DIR / "consolidado_despesas.zip"


def parseDecimal(valor: str) -> Decimal:
    v = (valor or "").strip()
    if not v:
        return Decimal(0)
    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def consolidarDespesas():
    stagingPath = getArquivoStaging()
    if not stagingPath.exists():
        raise RuntimeError("Staging não encontrado. Execute a normalização antes.")

    OUTPUT_TESTE1_DIR.mkdir(parents=True, exist_ok=True)

    csvFinal = getArquivoCsvFinal()
    zipFinal = getArquivoZipFinal()

    acumulado: Dict[Tuple[str, str, str], Decimal] = defaultdict(Decimal)

    with open(stagingPath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            registroAns = (row.get("reg_ans") or "").strip()
            ano = (row.get("ano") or "").strip()
            trimestre = (row.get("trimestre") or "").strip()

            if not registroAns or not ano or not trimestre:
                continue

            valor = parseDecimal(row.get("vl_saldo_final") or "0")
            if valor < 0:
                continue

            chave = (registroAns, ano, trimestre)
            acumulado[chave] += valor

    with open(csvFinal, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            ["RegistroANS", "RazaoSocial", "Trimestre", "Ano", "ValorDespesas"]
        )

        for (registroAns, ano, trimestre), valor in acumulado.items():
            writer.writerow([registroAns, "NÃO INFORMADA", trimestre, ano, str(valor)])

    with zipfile.ZipFile(zipFinal, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(csvFinal, arcname=csvFinal.name)

    return zipFinal


if __name__ == "__main__":
    print(f"Gerado: {consolidarDespesas()}")
