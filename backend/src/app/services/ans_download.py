from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin

import requests

baseUrl = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
userAgent = "v01dslick"


# Representa um trimestre com ano e numero do trimestre (1 a 4)
@dataclass(frozen=True, order=True)
class Trimestre:
    ano: int
    numero: int


# Representa um arquivo com URL, nome e trimestre
@dataclass
class Arquivo:
    url: str
    nome: str
    trimestre: Trimestre


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[4]


def getDiretorioSaida() -> Path:
    return getRaizProjeto() / "data/raw"


# Cria uma sessão HTTP com o user-agent configurado
def criarSessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": userAgent})
    return sessao


# Baixa o HTML da página para extrairmos os links
def baixarHtml(sessao: requests.Session, url: str) -> str:
    resposta = sessao.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.text


# Extrai os links do HTML baixado
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


# Extrai o trimestre do nome do arquivo
def extrairTrimestre(nomeArquivo: str, anoDaPasta: int) -> Trimestre | None:
    nome = nomeArquivo.lower()
    base = nome.split(".")[0]

    # normaliza separadores pra espaço
    for sep in ["-", "_"]:
        base = base.replace(sep, " ")
    tokens = [t for t in base.split() if t]

    # tenta achar ano 20xx em tokens (ou no começo de algo tipo 20130416)
    ano = None
    for t in tokens:
        if len(t) >= 4 and t[:4].isdigit() and t[:4].startswith("20"):
            ano = int(t[:4])
            break
    if ano is None:
        ano = anoDaPasta

    # caso com "t": 1t2017, 20130416 1t2012, 2013 1t, etc
    for t in tokens:
        if len(t) >= 2 and t[0] in "1234" and t[1] == "t":
            trimestre = int(t[0])
            return Trimestre(ano, trimestre)

    # caso com "trimestre"/"trim": 2007 1 trimestre, 3 trimestre, etc
    if "trimestre" in tokens or "trim" in tokens:
        for t in tokens:
            if t.isdigit():
                n = int(t)
                if 1 <= n <= 4:
                    return Trimestre(ano, n)

    return None


# Lista os arquivos do ano especificado
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
            Arquivo(
                url=urljoin(urlAno, link),
                nome=link,
                trimestre=trimestre,
            )
        )

    return arquivos


# Baixa os arquivos e salva na pasta destino (substitui arquivo no destino se já existir)
def baixarArquivo(sessao: requests.Session, arquivo: Arquivo, destino: Path):
    destinoTemp = destino.with_suffix(destino.suffix + ".part")

    with sessao.get(arquivo.url, stream=True, timeout=60) as resposta:
        resposta.raise_for_status()
        with open(destinoTemp, "wb") as f:
            for chunk in resposta.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    destinoTemp.replace(destino)


# Executa o download dos arquivos dos ultimos 3 trimestres disponíveis
def executarDownloadAns():
    sessao = criarSessao()
    diretorio = getDiretorioSaida()
    diretorio.mkdir(parents=True, exist_ok=True)
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
        for arquivo in arquivos:
            arquivosPorTrimestre.setdefault(arquivo.trimestre, []).append(arquivo)

    trimestresOrdenados = sorted(arquivosPorTrimestre.keys(), reverse=True)
    trimestresSelecionados = trimestresOrdenados[:3]

    for trimestre in trimestresSelecionados:
        for arquivo in arquivosPorTrimestre[trimestre]:
            destino = diretorio / arquivo.nome
            baixarArquivo(sessao, arquivo, destino)
            print(f"Baixado: {arquivo.nome}")


if __name__ == "__main__":
    executarDownloadAns()
