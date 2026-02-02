from pathlib import Path
from urllib.parse import urljoin

import pytest
from app.usecases.ans_download import (
    baixarHtml,
    baseUrl,
    criarSessao,
    extrairLinks,
)


def getRaizProjeto() -> Path:
    # backend/tests -> backend -> repo root
    return Path(__file__).resolve().parents[2]


def getDiretorioTmp() -> Path:
    return getRaizProjeto() / "data" / "tmp"


@pytest.mark.integration
def test_baixar_todos_os_arquivos_ans():
    sessao = criarSessao()
    diretorioTmp = getDiretorioTmp()
    diretorioTmp.mkdir(parents=True, exist_ok=True)

    falhas: list[str] = []

    try:
        htmlBase = baixarHtml(sessao, baseUrl)
        linksBase = extrairLinks(htmlBase)

        urlsAnos = [
            urljoin(baseUrl, link)
            for link in linksBase
            if link.endswith("/") and link[:-1].isdigit()
        ]

        for urlAno in urlsAnos:
            ano = urlAno.rstrip("/").split("/")[-1]
            print(f"\nAno {ano}")

            htmlAno = baixarHtml(sessao, urlAno)
            linksAno = extrairLinks(htmlAno)

            for link in linksAno:
                if link.endswith("/"):
                    continue
                if link.startswith("?"):
                    continue
                if ";" in link or "=" in link:
                    continue
                if link in ("../", "./"):
                    continue
                if not link.lower().endswith(".zip"):
                    continue

                urlArquivo = urljoin(urlAno, link)
                destino = diretorioTmp / link

                try:
                    with sessao.get(urlArquivo, stream=True, timeout=60) as resposta:
                        resposta.raise_for_status()
                        with open(destino, "wb") as f:
                            for chunk in resposta.iter_content(8192):
                                if chunk:
                                    f.write(chunk)

                    print(f"  ✅ {link}")

                except Exception as e:
                    falhas.append(f"{ano}/{link} -> {e}")
                    print(f"  ❌ {link} ({e})")

    finally:
        for arquivo in diretorioTmp.glob("*"):
            try:
                arquivo.unlink()
            except Exception as e:
                print(f"⚠️ Não foi possível apagar {arquivo.name}: {e}")

    if falhas:
        pytest.fail("Falhas ao baixar arquivos:\n" + "\n".join(falhas))
