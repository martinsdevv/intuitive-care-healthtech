import csv
import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Optional

import requests

userAgent = "v01dslick"
cadopBaseUrl = (
    "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
)
cadopFileName = "Relatorio_cadop.csv"


@dataclass(frozen=True)
class CadopRegistro:
    registroAns: str
    cnpj: str
    razaoSocial: str
    modalidade: str
    uf: str


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[4]


def getDiretorioRaw() -> Path:
    return getRaizProjeto() / "data/raw"


def getDiretorioOutputBase() -> Path:
    return getRaizProjeto() / "data/output"


def getDiretorioOutputTeste1() -> Path:
    return getDiretorioOutputBase() / "teste1"


def getDiretorioOutputTeste2() -> Path:
    return getDiretorioOutputBase() / "teste2"


def getArquivoConsolidado() -> Path:
    # INPUT do Teste 2 vem do OUTPUT do Teste 1
    return getDiretorioOutputTeste1() / "consolidado_despesas.csv"


def getArquivoCadopLocal() -> Path:
    return getDiretorioRaw() / cadopFileName


def getArquivoFinalTeste2() -> Path:
    # OUTPUT do Teste 2
    return getDiretorioOutputTeste2() / "consolidado_despesas_final.csv"


def criarSessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": userAgent})
    return sessao


def baixarCadopSeNecessario() -> Path:
    destino = getArquivoCadopLocal()
    if destino.exists():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)

    url = cadopBaseUrl.rstrip("/") + "/" + cadopFileName
    destinoTemp = destino.with_suffix(destino.suffix + ".part")

    sessao = criarSessao()
    with sessao.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(destinoTemp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    destinoTemp.replace(destino)
    return destino


def detectarEncoding(caminho: Path) -> str:
    amostra = caminho.read_bytes()[:200_000]
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def normalizarHeader(nome: str) -> str:
    nome = (nome or "").strip().lower()
    nome = re.sub(r"\s+", " ", nome)
    nome = nome.replace("ã", "a").replace("á", "a").replace("à", "a")
    nome = nome.replace("é", "e").replace("ê", "e")
    nome = nome.replace("í", "i")
    nome = nome.replace("ó", "o").replace("ô", "o")
    nome = nome.replace("ú", "u")
    nome = nome.replace("ç", "c")
    nome = nome.replace(" ", "_")
    return nome


def limparDigitos(valor: str) -> str:
    return re.sub(r"\D+", "", valor or "")


def parseDecimal(valor: str) -> Optional[Decimal]:
    v = (valor or "").strip()
    if not v:
        return None
    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return None


def validarCnpj(cnpj: str) -> bool:
    cnpj = limparDigitos(cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def calcDv(base: str) -> str:
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        soma = 0
        for i, p in enumerate(pesos1):
            soma += int(base[i]) * p
        resto = soma % 11
        dv1 = "0" if resto < 2 else str(11 - resto)

        base2 = base + dv1
        soma = 0
        for i, p in enumerate(pesos2):
            soma += int(base2[i]) * p
        resto = soma % 11
        dv2 = "0" if resto < 2 else str(11 - resto)

        return dv1 + dv2

    base = cnpj[:12]
    dv = cnpj[12:]
    return calcDv(base) == dv


def escolherMaisCompleto(a: CadopRegistro, b: CadopRegistro) -> CadopRegistro:
    def score(x: CadopRegistro) -> int:
        s = 0
        s += 1 if x.cnpj else 0
        s += 1 if x.razaoSocial else 0
        s += 1 if x.modalidade else 0
        s += 1 if x.uf else 0
        return s

    sa = score(a)
    sb = score(b)
    if sb > sa:
        return b
    return a


def carregarCadopPorRegistroAns(cadopPath: Path) -> Dict[str, CadopRegistro]:
    encoding = detectarEncoding(cadopPath)

    with open(cadopPath, encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        header = next(reader, [])
        if not header:
            return {}

        idx: Dict[str, int] = {}
        for i, h in enumerate(header):
            idx[normalizarHeader(h)] = i

        def get(row, key):
            i = idx.get(key)
            if i is None or i >= len(row):
                return ""
            return (row[i] or "").strip()

        out: Dict[str, CadopRegistro] = {}

        for row in reader:
            registroAns = limparDigitos(
                get(row, "registro_ans") or get(row, "registro_operadora")
            )
            if not registroAns:
                continue

            item = CadopRegistro(
                registroAns=registroAns,
                cnpj=limparDigitos(get(row, "cnpj")),
                razaoSocial=get(row, "razao_social"),
                modalidade=get(row, "modalidade"),
                uf=get(row, "uf"),
            )

            if registroAns in out:
                out[registroAns] = escolherMaisCompleto(out[registroAns], item)
            else:
                out[registroAns] = item

        return out


def detectarDelimiter(caminho: Path) -> str:
    amostra = caminho.read_text(encoding=detectarEncoding(caminho), errors="ignore")[
        :50_000
    ]
    return ";" if amostra.count(";") > amostra.count(",") else ","


def executarEnriquecimentoEValidacao() -> Path:
    consolidadoPath = getArquivoConsolidado()
    if not consolidadoPath.exists():
        raise RuntimeError(
            "consolidado_despesas.csv não encontrado em data/output/teste1. Rode o Teste 1 primeiro."
        )

    cadopPath = baixarCadopSeNecessario()
    cadop = carregarCadopPorRegistroAns(cadopPath)

    outPath = getArquivoFinalTeste2()

    # ✅ garante que data/output/teste2 existe antes de abrir o arquivo
    outPath.parent.mkdir(parents=True, exist_ok=True)

    consolidadoEnc = detectarEncoding(consolidadoPath)
    delim = detectarDelimiter(consolidadoPath)

    with (
        open(consolidadoPath, encoding=consolidadoEnc, newline="") as fIn,
        open(outPath, "w", encoding="utf-8", newline="") as fOut,
    ):
        reader = csv.DictReader(fIn, delimiter=delim)
        fieldnames = [
            "RegistroANS",
            "CNPJ",
            "RazaoSocial",
            "Modalidade",
            "UF",
            "Trimestre",
            "Ano",
            "ValorDespesas",
            "cnpj_valido",
            "valor_positivo",
            "razao_social_nao_vazia",
            "erros",
        ]
        writer = csv.DictWriter(fOut, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()

        for row in reader:
            registroAns = limparDigitos(
                row.get("RegistroANS") or row.get("reg_ans") or ""
            )
            trimestre = (row.get("Trimestre") or row.get("trimestre") or "").strip()
            ano = (row.get("Ano") or row.get("ano") or "").strip()
            valorStr = (
                row.get("ValorDespesas")
                or row.get("valorDespesas")
                or row.get("valor_despesas")
                or ""
            ).strip()

            cad = cadop.get(registroAns)
            cnpj = cad.cnpj if cad else ""
            razaoSocial = cad.razaoSocial if cad else ""
            modalidade = cad.modalidade if cad else ""
            uf = cad.uf if cad else ""

            erros = []

            cnpjOk = validarCnpj(cnpj) if cnpj else False
            if not cnpjOk:
                erros.append("cnpj_invalido")

            valor = parseDecimal(valorStr)
            valorOk = bool(valor is not None and valor > 0)
            if not valorOk:
                erros.append("valor_nao_positivo")

            razaoOk = bool((razaoSocial or "").strip())
            if not razaoOk:
                erros.append("razao_social_vazia")

            writer.writerow(
                {
                    "RegistroANS": registroAns,
                    "CNPJ": cnpj,
                    "RazaoSocial": razaoSocial,
                    "Modalidade": modalidade,
                    "UF": uf,
                    "Trimestre": trimestre,
                    "Ano": ano,
                    "ValorDespesas": valorStr,
                    "cnpj_valido": "1" if cnpjOk else "0",
                    "valor_positivo": "1" if valorOk else "0",
                    "razao_social_nao_vazia": "1" if razaoOk else "0",
                    "erros": ",".join(erros),
                }
            )

    zipPath = outPath.with_suffix(".zip")
    with zipfile.ZipFile(zipPath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(outPath, arcname=outPath.name)

    return outPath


if __name__ == "__main__":
    out = executarEnriquecimentoEValidacao()
    print(f"Gerado: {out}")
