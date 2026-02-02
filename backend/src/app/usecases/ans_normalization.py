import csv
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from app.core.paths import EXTRACTED_DIR, RAW_DIR, STAGING_DIR
from app.core.types import Trimestre
from app.usecases.ans_download import executarDownloadAns


@dataclass(frozen=True)
class ZipJob:
    zipPath: Path
    trimestre: Optional[Trimestre]


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


def parseDecimalStr(valor: str) -> str:
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
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(enc)
            return enc
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

    with zipfile.ZipFile(caminhoZip, "r") as z:
        for info in z.infolist():
            if info.filename.endswith("/"):
                continue
            destinoArquivo = destino / Path(info.filename).name
            with z.open(info) as origem, open(destinoArquivo, "wb") as saida:
                saida.write(origem.read())
            arquivos.append(destinoArquivo)

    return arquivos


def normalizarNomeColuna(nome: str) -> str:
    nome = stripAccents(nome).upper()
    return re.sub(r"\s+", "_", nome)


def indexarColunas(header: List[str]) -> dict[str, int]:
    idx: dict[str, int] = {}
    for i, nome in enumerate(header):
        idx[normalizarNomeColuna(nome)] = i
    return idx


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
            i = colunas.get(key)
            if i is None or i >= len(row):
                return ""
            return row[i]

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
                    parseDecimalStr(get(row, "VL_SALDO_INICIAL"))
                    if "VL_SALDO_INICIAL" in colunas
                    else "",
                    parseDecimalStr(get(row, "VL_SALDO_FINAL")),
                    str(trimestre.ano) if trimestre else "",
                    str(trimestre.numero) if trimestre else "",
                    caminhoCsv.name,
                ]
            )

    return {"total": total, "match": match}


def listarZipsRaw() -> List[ZipJob]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    jobs: List[ZipJob] = []

    for zipPath in sorted(RAW_DIR.glob("*.zip")):
        jobs.append(
            ZipJob(
                zipPath=zipPath,
                trimestre=inferirTrimestreDoZip(zipPath.name),
            )
        )

    return jobs


def executarProcessamentoAns() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not any(RAW_DIR.glob("*.zip")):
        executarDownloadAns()

    stagingPath = STAGING_DIR / "eventos_sinistros_staging.csv"

    jobs = listarZipsRaw()
    if not jobs:
        raise RuntimeError("Nenhum ZIP encontrado em data/raw")

    for job in jobs:
        trimestre = job.trimestre or inferirTrimestreDoZip(job.zipPath.name)
        destino = EXTRACTED_DIR / (
            f"{trimestre.numero}T{trimestre.ano}" if trimestre else job.zipPath.stem
        )

        arquivos = extrairZip(job.zipPath, destino)

        csvs = [a for a in arquivos if a.suffix.lower() == ".csv"]
        naoCsv = [a for a in arquivos if a.suffix.lower() != ".csv"]

        if naoCsv:
            exts = sorted({p.suffix.lower() or "<sem_ext>" for p in naoCsv})
            print(f"{job.zipPath.name} | arquivos não-CSV detectados: {exts}")

        if not csvs:
            print(f"{job.zipPath.name} | nenhum CSV encontrado (ignorando)")
            continue

        for csvPath in csvs:
            stats = processarCsvParaStaging(csvPath, stagingPath, trimestre)
            print(f"{csvPath.name} | lidas={stats['total']} | match={stats['match']}")

    return stagingPath


if __name__ == "__main__":
    executarProcessamentoAns()
