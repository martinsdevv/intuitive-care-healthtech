from dataclasses import dataclass
from typing import Dict, List
from urllib.parse import urljoin

import requests
from app.core.paths import RAW_DIR
from app.core.types import Trimestre

baseUrl = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
userAgent = "v01dslick"


@dataclass
class Arquivo:
    url: str
    nome: str
    trimestre: Trimestre


def criarSessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": userAgent})
    return sessao


def baixarHtml(sessao: requests.Session, url: str) -> str:
    resp = sessao.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def extrairLinks(html: str) -> List[str]:
    links: List[str] = []
    for linha in html.splitlines():
        if "href" not in linha:
            continue
        inicio = linha.find('href="') + 6
        fim = linha.find('"', inicio)
        links.append(linha[inicio:fim])
    return links


def isDiretorioAno(nome: str) -> bool:
    return nome.isdigit() and len(nome) == 4


def extrairTrimestre(nomeArquivo: str, anoDaPasta: int) -> Trimestre | None:
    nome = nomeArquivo.lower()
    base = nome.split(".")[0]

    for sep in ["-", "_"]:
        base = base.replace(sep, " ")
    tokens = [t for t in base.split() if t]

    ano = None
    for t in tokens:
        if len(t) >= 4 and t[:4].isdigit() and t[:4].startswith("20"):
            ano = int(t[:4])
            break
    if ano is None:
        ano = anoDaPasta

    for t in tokens:
        if len(t) >= 2 and t[0] in "1234" and t[1] == "t":
            return Trimestre(ano, int(t[0]))

    if "trimestre" in tokens or "trim" in tokens:
        for t in tokens:
            if t.isdigit():
                n = int(t)
                if 1 <= n <= 4:
                    return Trimestre(ano, n)

    return None


def listarArquivosAno(
    sessao: requests.Session, urlAno: str, anoDaPasta: int
) -> List[Arquivo]:
    html = baixarHtml(sessao, urlAno)
    links = extrairLinks(html)
    arquivos: List[Arquivo] = []

    for link in links:
        if link.endswith("/"):
            continue

        trimestre = extrairTrimestre(link, anoDaPasta)
        if not trimestre:
            continue

        arquivos.append(
            Arquivo(url=urljoin(urlAno, link), nome=link, trimestre=trimestre)
        )

    return arquivos


def baixarArquivo(sessao: requests.Session, arquivo: Arquivo, destino):
    destinoTemp = destino.with_suffix(destino.suffix + ".part")

    with sessao.get(arquivo.url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(destinoTemp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    destinoTemp.replace(destino)


def executarDownloadAns() -> None:
    sessao = criarSessao()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    htmlBase = baixarHtml(sessao, baseUrl)
    linksBase = extrairLinks(htmlBase)

    urlsAnos: List[str] = []
    for link in linksBase:
        if link.endswith("/") and isDiretorioAno(link[:-1]):
            urlsAnos.append(urljoin(baseUrl, link))

    arquivosPorTrimestre: Dict[Trimestre, List[Arquivo]] = {}

    for urlAno in urlsAnos:
        anoDaPasta = int(urlAno.rstrip("/").split("/")[-1])
        arquivos = listarArquivosAno(sessao, urlAno, anoDaPasta)
        for a in arquivos:
            arquivosPorTrimestre.setdefault(a.trimestre, []).append(a)

    trimestresOrdenados = sorted(arquivosPorTrimestre.keys(), reverse=True)
    trimestresSelecionados = trimestresOrdenados[:3]

    for trimestre in trimestresSelecionados:
        for arquivo in arquivosPorTrimestre[trimestre]:
            destino = RAW_DIR / arquivo.nome
            baixarArquivo(sessao, arquivo, destino)
            print(f"Baixado: {arquivo.nome}")


if __name__ == "__main__":
    executarDownloadAns()
