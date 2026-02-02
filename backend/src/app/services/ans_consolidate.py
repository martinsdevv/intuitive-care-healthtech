import csv
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Tuple


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[4]


def getDiretorioStaging() -> Path:
    return getRaizProjeto() / "data/staging"


def getDiretorioFinal() -> Path:
    return getRaizProjeto() / "data/output"


def getArquivoStaging() -> Path:
    return getDiretorioStaging() / "eventos_sinistros_staging.csv"


def getArquivoCsvFinal() -> Path:
    return getDiretorioFinal() / "consolidado_despesas.csv"


def getArquivoZipFinal() -> Path:
    return getDiretorioFinal() / "consolidado_despesas.zip"


def parseDecimal(valor: str) -> Decimal:
    valor = (valor or "").strip()
    if not valor:
        return Decimal(0)
    try:
        return Decimal(valor)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def consolidarDespesas() -> Path:
    stagingPath = getArquivoStaging()
    if not stagingPath.exists():
        raise RuntimeError("Staging não encontrado. Execute a normalização antes.")

    diretorioFinal = getDiretorioFinal()
    diretorioFinal.mkdir(parents=True, exist_ok=True)

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
        writer = csv.writer(f)
        writer.writerow(
            ["RegistroANS", "RazaoSocial", "Trimestre", "Ano", "ValorDespesas"]
        )

        for (registroAns, ano, trimestre), valor in acumulado.items():
            writer.writerow(
                [
                    registroAns,
                    "NÃO INFORMADA",
                    trimestre,
                    ano,
                    str(valor),
                ]
            )

    with zipfile.ZipFile(zipFinal, "w", zipfile.ZIP_DEFLATED) as zipFile:
        zipFile.write(csvFinal, arcname=csvFinal.name)

    return zipFinal


if __name__ == "__main__":
    zipGerado = consolidarDespesas()
    print(f"Arquivo final gerado em: {zipGerado}")
