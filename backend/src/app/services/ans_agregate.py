import csv
import os
import re
import zipfile
from configparser import DEFAULTSECT
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Optional, Tuple
from webbrowser import get

DEFAULT_ZIP_NOME = "Agregacao_Gabriel_Martins"
INPUT_FILENAME = "consolidado_despesas_final.csv"
OUTPUT_FILENAME = "despesas_agregadas.csv"


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[4]


def getDiretorioOutput() -> Path:
    return getRaizProjeto() / "data" / "output" / "teste2"


def getDiretorioDelivery() -> Path:
    return getRaizProjeto() / "delivery"


def getArquivoInput() -> Path:
    return getDiretorioOutput() / INPUT_FILENAME


def getArquivoCsvAgregado() -> Path:
    return getDiretorioOutput() / OUTPUT_FILENAME


def getArquivoZipFinal(nome: Optional[str] = None) -> Path:
    nome = DEFAULT_ZIP_NOME
    nome = re.sub(r"[^A-Za-z0-9_-]+", "_", nome)
    return getDiretorioOutput() / f"Teste_{nome}.zip"


def detectarEncoding(caminho: Path) -> str:
    amostra = caminho.read_bytes()[:200_000]
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detectarDelimiter(caminho: Path, encoding: str) -> str:
    amostra = caminho.read_text(encoding=encoding, errors="ignore")[:50_000]
    return ";" if amostra.count(";") >= amostra.count(",") else ","


def parseDecimal(valor: str) -> Optional[Decimal]:
    v = (valor or "").strip()
    if not v:
        return None

    v = v.replace(" ", "")
    if "," in v and "." in v:
        # ex: 1.234.567,89
        v = v.replace(".", "").replace(",", ".")
    elif "," in v and "." not in v:
        # ex: 123,45
        v = v.replace(",", ".")

    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return None


@dataclass
class WelfordAgg:
    """
    Estatística online por grupo:
    mantém total, média e M2 para obter desvio padrão (populacional) em 1 passagem.
    """

    n: int = 0
    mean: Decimal = Decimal("0")
    m2: Decimal = Decimal("0")
    total: Decimal = Decimal("0")

    def add(self, x: Decimal) -> None:
        self.total += x
        self.n += 1
        delta = x - self.mean
        self.mean += delta / Decimal(self.n)
        delta2 = x - self.mean
        self.m2 += delta * delta2

    def variance_pop(self) -> Decimal:
        if self.n == 0:
            return Decimal("0")
        return self.m2 / Decimal(self.n)

    def std_pop(self) -> Decimal:
        v = self.variance_pop()
        return v.sqrt() if v > 0 else Decimal("0")


def _linha_valida(row: dict) -> bool:
    if (row.get("valor_positivo") or "") != "1":
        return False
    if (row.get("razao_social_nao_vazia") or "") != "1":
        return False
    if not (row.get("UF") or "").strip():
        return False
    return True


def executarAgregacaoAns(nome_zip: Optional[str] = None) -> Tuple[Path, Path]:
    inp = getArquivoInput()
    if not inp.exists():
        raise RuntimeError(
            f"Arquivo de entrada não encontrado: {inp}. Rode o Teste 2.2/2.1 antes."
        )

    out_dir = getDiretorioOutput()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_csv = getArquivoCsvAgregado()
    out_zip = getArquivoZipFinal(nome_zip)

    # ✅ garante delivery existir (resolve o erro do --clean)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    enc = detectarEncoding(inp)
    delim = detectarDelimiter(inp, enc)

    grupos: Dict[tuple[str, str], WelfordAgg] = {}

    with open(inp, newline="", encoding=enc) as f:
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            if not _linha_valida(row):
                continue

            razao = (row.get("RazaoSocial") or "").strip()
            uf = (row.get("UF") or "").strip()

            valor = parseDecimal(row.get("ValorDespesas") or "")
            if valor is None:
                continue

            key = (razao, uf)
            agg = grupos.get(key)
            if agg is None:
                agg = WelfordAgg()
                grupos[key] = agg
            agg.add(valor)

    registros = []
    for (razao, uf), agg in grupos.items():
        registros.append(
            {
                "RazaoSocial": razao,
                "UF": uf,
                "total_despesas": str(agg.total.quantize(Decimal("0.01"))),
                "media_trimestral": str(agg.mean.quantize(Decimal("0.01"))),
                "desvio_padrao": str(agg.std_pop().quantize(Decimal("0.01"))),
                "qtd_registros": str(agg.n),
            }
        )

    registros.sort(key=lambda r: Decimal(r["total_despesas"]), reverse=True)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "RazaoSocial",
                "UF",
                "total_despesas",
                "media_trimestral",
                "desvio_padrao",
                "qtd_registros",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(registros)

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(out_csv, arcname=out_csv.name)

    return out_csv, out_zip


if __name__ == "__main__":
    csv_path, zip_path = executarAgregacaoAns()
    print(f"Gerado CSV: {csv_path}")
    print(f"Gerado ZIP: {zip_path}")
