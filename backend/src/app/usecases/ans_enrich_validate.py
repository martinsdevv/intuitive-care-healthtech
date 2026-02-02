import csv
import re
import zipfile
from pathlib import Path
from typing import Dict

import requests
from app.core.paths import OUTPUT_TESTE1_DIR, OUTPUT_TESTE2_DIR, RAW_DIR
from app.domain.models import CadopRegistro
from app.domain.validators import limpar_digitos, parse_decimal, validar_cnpj

userAgent = "v01dslick"
cadopBaseUrl = (
    "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
)
cadopFileName = "Relatorio_cadop.csv"


def getArquivoConsolidado() -> Path:
    return OUTPUT_TESTE1_DIR / "consolidado_despesas.csv"


def getArquivoCadopLocal() -> Path:
    return RAW_DIR / cadopFileName


def getArquivoFinalTeste2() -> Path:
    return OUTPUT_TESTE2_DIR / "consolidado_despesas_final.csv"


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
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detectarDelimiter(caminho: Path) -> str:
    amostra = caminho.read_text(encoding=detectarEncoding(caminho), errors="ignore")[
        :50_000
    ]
    return ";" if amostra.count(";") > amostra.count(",") else ","


def normalizarHeader(nome: str) -> str:
    nome = (nome or "").strip().lower()
    nome = re.sub(r"\s+", " ", nome)
    nome = (
        nome.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return nome.replace(" ", "_")


def escolherMaisCompleto(a: CadopRegistro, b: CadopRegistro) -> CadopRegistro:
    def score(x: CadopRegistro) -> int:
        s = 0
        s += 1 if x.cnpj else 0
        s += 1 if x.razaoSocial else 0
        s += 1 if x.modalidade else 0
        s += 1 if x.uf else 0
        return s

    return b if score(b) > score(a) else a


def carregarCadopPorRegistroAns(cadopPath: Path) -> Dict[str, CadopRegistro]:
    enc = detectarEncoding(cadopPath)

    with open(cadopPath, encoding=enc, newline="") as f:
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
            registroAns = limpar_digitos(
                get(row, "registro_ans") or get(row, "registro_operadora")
            )
            if not registroAns:
                continue

            item = CadopRegistro(
                registroAns=registroAns,
                cnpj=limpar_digitos(get(row, "cnpj")),
                razaoSocial=get(row, "razao_social"),
                modalidade=get(row, "modalidade"),
                uf=get(row, "uf"),
            )

            if registroAns in out:
                out[registroAns] = escolherMaisCompleto(out[registroAns], item)
            else:
                out[registroAns] = item

        return out


def executarEnriquecimentoEValidacao() -> Path:
    consolidadoPath = getArquivoConsolidado()
    if not consolidadoPath.exists():
        raise RuntimeError(
            "consolidado_despesas.csv não encontrado em data/output/teste1. Rode o Teste 1 primeiro."
        )

    cadopPath = baixarCadopSeNecessario()
    cadop = carregarCadopPorRegistroAns(cadopPath)

    outPath = getArquivoFinalTeste2()
    outPath.parent.mkdir(parents=True, exist_ok=True)

    enc = detectarEncoding(consolidadoPath)
    delim = detectarDelimiter(consolidadoPath)

    with (
        open(consolidadoPath, encoding=enc, newline="") as fIn,
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
            registroAns = limpar_digitos(
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

            cnpjOk = validar_cnpj(cnpj) if cnpj else False
            if not cnpjOk:
                erros.append("cnpj_invalido")

            valor = parse_decimal(valorStr)
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
    print(f"Gerado: {executarEnriquecimentoEValidacao()}")
