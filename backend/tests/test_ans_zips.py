from __future__ import annotations

import os
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import pytest
from app.services.ans_download import (
    baixarHtml,
    baseUrl,
    criarSessao,
    extrairLinks,
)

KEYWORDS_DESPESAS = (
    "desp",
    "despesa",
    "sinistro",
    "evento",
    "eventos",
    "assist",
    "assistencial",
)


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[2]


def getDiretorioTmp() -> Path:
    return getRaizProjeto() / "data" / "tmp"


def _is_dir_ano(link: str) -> bool:
    return link.endswith("/") and link[:-1].isdigit() and len(link[:-1]) == 4


def _is_zip_file(link: str) -> bool:
    if link.endswith("/"):
        return False
    if link.startswith("?"):
        return False
    if ";" in link or "=" in link:
        return False
    if link in ("../", "./"):
        return False
    return link.lower().endswith(".zip")


def _pick_years(anos: list[str], max_anos: int) -> list[str]:
    anos = sorted(set(anos))
    if not anos:
        return []

    # sempre inclui menor e maior
    chosen = [anos[0]]
    if anos[-1] != anos[0]:
        chosen.append(anos[-1])

    # adiciona anos do meio, espaçados
    if len(chosen) < max_anos and len(anos) > 2:
        remaining = [a for a in anos[1:-1]]
        if remaining:
            step = max(1, len(remaining) // max(1, (max_anos - len(chosen))))
            chosen.extend(remaining[::step])

    return chosen[:max_anos]


@dataclass
class ZipInventory:
    ano: str
    zip_name: str
    inner_count: int
    extensions: Counter
    candidates_by_name: int
    largest_inner: list[tuple[str, int]]


@pytest.mark.integration
def test_ans_inventory_baixar_extrair_amostra():
    sessao = criarSessao()
    tmp = getDiretorioTmp()
    tmp.mkdir(parents=True, exist_ok=True)

    # Configurações acerca de quantos arquivos baixar, e se irá manter os arquivos baixados ou não
    # Crie as variaveis de ambiente ou mude os valores fallback
    max_anos = int(os.getenv("ANS_MAX_ANOS", "10"))
    max_zips_por_ano = int(os.getenv("ANS_MAX_ZIPS_POR_ANO", "2"))
    # 0: apagar arquivos baixados
    # 1: manter arquivos baixados
    keep_tmp = os.getenv("ANS_KEEP_TMP", "1") == "1"

    falhas: list[str] = []
    inventories: list[ZipInventory] = []

    try:
        html_base = baixarHtml(sessao, baseUrl)
        links_base = extrairLinks(html_base)

        anos = [link[:-1] for link in links_base if _is_dir_ano(link)]
        anos_escolhidos = _pick_years(anos, max_anos)

        assert anos_escolhidos, "Nenhum ano encontrado no diretório base da ANS."

        for ano in anos_escolhidos:
            url_ano = urljoin(baseUrl, f"{ano}/")
            print(f"\nAno {ano} ({url_ano})")

            html_ano = baixarHtml(sessao, url_ano)
            links_ano = extrairLinks(html_ano)
            zips = [l for l in links_ano if _is_zip_file(l)]
            zips = sorted(zips)[:max_zips_por_ano]

            if not zips:
                print("  ⚠️ Nenhum ZIP encontrado nesse ano (ou filtro falhou).")
                continue

            for zip_name in zips:
                url_zip = urljoin(url_ano, zip_name)
                zip_path = tmp / f"{ano}__{zip_name}"

                try:
                    with sessao.get(url_zip, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        with open(zip_path, "wb") as f:
                            for chunk in r.iter_content(8192):
                                if chunk:
                                    f.write(chunk)

                    extensions = Counter()
                    candidates_by_name = 0
                    inner_sizes: list[tuple[str, int]] = []

                    with zipfile.ZipFile(zip_path, "r") as zf:
                        infos = zf.infolist()
                        for info in infos:
                            name = info.filename
                            if name.endswith("/"):
                                continue
                            ext = Path(name).suffix.lower() or "<none>"
                            extensions[ext] += 1
                            inner_sizes.append((name, info.file_size))

                            low = name.lower()
                            if any(k in low for k in KEYWORDS_DESPESAS):
                                candidates_by_name += 1

                    inner_sizes.sort(key=lambda x: x[1], reverse=True)
                    largest_inner = inner_sizes[:5]

                    inventories.append(
                        ZipInventory(
                            ano=ano,
                            zip_name=zip_name,
                            inner_count=sum(extensions.values()),
                            extensions=extensions,
                            candidates_by_name=candidates_by_name,
                            largest_inner=largest_inner,
                        )
                    )

                    print(
                        f"  ✅ {zip_name} | inner={sum(extensions.values())} | ext={dict(extensions)} | cand={candidates_by_name}"
                    )
                    for n, sz in largest_inner:
                        print(f"     - {n} ({sz} bytes)")

                except Exception as e:
                    falhas.append(f"{ano}/{zip_name} -> {e}")
                    print(f"  ❌ {zip_name} ({e})")

        # resumo geral
        if inventories:
            ext_total = Counter()
            for inv in inventories:
                ext_total.update(inv.extensions)
            print("\nResumo geral (amostra):")
            print(f"  Zips analisados: {len(inventories)}")
            print(f"  Extensões (total): {dict(ext_total)}")

    finally:
        if not keep_tmp:
            for p in tmp.glob("*"):
                try:
                    p.unlink()
                except Exception as e:
                    print(f"⚠️ Não foi possível apagar {p.name}: {e}")

    if falhas:
        pytest.fail("Falhas no inventory:\n" + "\n".join(falhas))
