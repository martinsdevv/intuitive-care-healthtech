import csv
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from ans_download import (
    Trimestre,
    executarDownloadAns,
)
from ans_download import (
    getDiretorioSaida as getDiretorioRaw,
)


@dataclass(frozen=True)
class ZipJob:
    zipPath: Path
    trimestre: Optional[Trimestre]


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[4]


def getDiretorioExtracted() -> Path:
    return getRaizProjeto() / "data/extracted"


def getDiretorioStaging() -> Path:
    return getRaizProjeto() / "data/staging"


def stripAccents(valor: str) -> str:
    nfkd = unicodedata.normalize("NFKD", valor)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizarTexto(valor: str) -> str:
    valor = stripAccents(valor)
    valor = re.sub(r"\s+", " ", valor)
    return valor.lower().strip()


def isDespesasEventosSinistros(descricao: str) -> bool:
    texto = normalizarTexto(descricao)
    return "desp" in texto and ("evento" in texto or "sinistro" in texto)


def parseData(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        return ""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            pass
    return valor


def parseDecimal(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        return ""
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return str(Decimal(valor))
    except (InvalidOperation, ValueError):
        return valor


def detectarEncoding(caminho: Path) -> str:
    amostra = caminho.read_bytes()[:200_000]
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def inferirTrimestreDoZip(nome: str) -> Optional[Trimestre]:
    nome = nome.lower()

    match = re.search(r"([1-4])t(20\d{2})", nome)
    if match:
        return Trimestre(int(match.group(2)), int(match.group(1)))

    match = re.search(r"(20\d{2}).*?([1-4]).*?(trimestre|trim)", nome)
    if match:
        return Trimestre(int(match.group(1)), int(match.group(2)))

    return None


def extrairZip(caminhoZip: Path, destino: Path) -> List[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos: List[Path] = []

    with zipfile.ZipFile(caminhoZip, "r") as zipFile:
        for info in zipFile.infolist():
            if info.filename.endswith("/"):
                continue
            destinoArquivo = destino / Path(info.filename).name
            with zipFile.open(info) as origem, open(destinoArquivo, "wb") as saida:
                saida.write(origem.read())
            arquivos.append(destinoArquivo)

    return arquivos


def normalizarNomeColuna(nome: str) -> str:
    nome = stripAccents(nome).upper()
    return re.sub(r"\s+", "_", nome)


def indexarColunas(header: List[str]) -> dict[str, int]:
    indices: dict[str, int] = {}
    for i, nome in enumerate(header):
        indices[normalizarNomeColuna(nome)] = i
    return indices


CANON_HEADER = [
    "data",
    "reg_ans",
    "cd_conta_contabil",
    "descricao",
    "vl_saldo_inicial",
    "vl_saldo_final",
    "ano",
    "trimestre",
    "fonte_arquivo",
]


def processarCsvParaStaging(
    caminhoCsv: Path,
    caminhoStaging: Path,
    trimestre: Optional[Trimestre],
) -> dict:
    encoding = detectarEncoding(caminhoCsv)
    caminhoStaging.parent.mkdir(parents=True, exist_ok=True)
    existe = caminhoStaging.exists()

    total = 0
    match = 0

    with (
        open(caminhoCsv, encoding=encoding, newline="") as entrada,
        open(caminhoStaging, "a", encoding="utf-8", newline="") as saida,
    ):
        reader = csv.reader(entrada, delimiter=";", quotechar='"')
        writer = csv.writer(saida)

        try:
            header = next(reader)
        except StopIteration:
            return {"total": 0, "match": 0}

        if not existe:
            writer.writerow(CANON_HEADER)

        colunas = indexarColunas(header)

        def get(row: List[str], key: str) -> str:
            idx = colunas.get(key)
            if idx is None or idx >= len(row):
                return ""
            return row[idx]

        for row in reader:
            total += 1
            descricao = get(row, "DESCRICAO")
            if not descricao or not isDespesasEventosSinistros(descricao):
                continue

            match += 1

            writer.writerow(
                [
                    parseData(get(row, "DATA")),
                    get(row, "REG_ANS").strip(),
                    get(row, "CD_CONTA_CONTABIL").strip(),
                    descricao.strip(),
                    parseDecimal(get(row, "VL_SALDO_INICIAL"))
                    if "VL_SALDO_INICIAL" in colunas
                    else "",
                    parseDecimal(get(row, "VL_SALDO_FINAL")),
                    str(trimestre.ano) if trimestre else "",
                    str(trimestre.numero) if trimestre else "",
                    caminhoCsv.name,
                ]
            )

    return {"total": total, "match": match}


def listarZipsRaw() -> List[ZipJob]:
    diretorio = getDiretorioRaw()
    diretorio.mkdir(parents=True, exist_ok=True)
    jobs: List[ZipJob] = []

    for zipPath in sorted(diretorio.glob("*.zip")):
        jobs.append(
            ZipJob(
                zipPath=zipPath,
                trimestre=inferirTrimestreDoZip(zipPath.name),
            )
        )

    return jobs


def executarProcessamentoAns() -> Path:
    raw = getDiretorioRaw()
    raw.mkdir(parents=True, exist_ok=True)

    if not any(raw.glob("*.zip")):
        executarDownloadAns()

    extractedRoot = getDiretorioExtracted()
    stagingPath = getDiretorioStaging() / "eventos_sinistros_staging.csv"

    jobs = listarZipsRaw()
    if not jobs:
        raise RuntimeError("Nenhum ZIP encontrado em data/raw")

    for job in jobs:
        trimestre = job.trimestre or inferirTrimestreDoZip(job.zipPath.name)
        destino = extractedRoot / (
            f"{trimestre.numero}T{trimestre.ano}" if trimestre else job.zipPath.stem
        )

        arquivos = extrairZip(job.zipPath, destino)
        csvs = [a for a in arquivos if a.suffix.lower() == ".csv"]

        for csvPath in csvs:
            stats = processarCsvParaStaging(csvPath, stagingPath, trimestre)
            print(f"{csvPath.name} | lidas={stats['total']} | match={stats['match']}")

    return stagingPath


if __name__ == "__main__":
    executarProcessamentoAns()
