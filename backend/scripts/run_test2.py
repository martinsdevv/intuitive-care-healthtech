import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
sys.path.insert(0, str(SRC))

import argparse
import shutil

from app.services.ans_agregate import executarAgregacaoAns
from app.services.ans_enrich_validate import executarEnriquecimentoEValidacao


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[2]


def getOutputTeste2() -> Path:
    return getRaizProjeto() / "data/output/teste2"


def getDeliveryDir() -> Path:
    return getRaizProjeto() / "delivery"


def limparTeste2(nome: str):
    """
    Clean do Teste 2:
    - Remove apenas data/output/teste2
    - NÃO remove a pasta delivery
    - Opcional: remove só o zip de entrega específico (se existir)
    """
    out = getOutputTeste2()
    if out.exists():
        shutil.rmtree(out)
        print(f"Removido: {out}")

    # remove apenas o arquivo de entrega, não a pasta
    delivery_zip = getDeliveryDir() / f"Teste_Agregacao_{nome}.zip"
    if delivery_zip.exists():
        delivery_zip.unlink()
        print(f"Removido: {delivery_zip}")


def main(clean: bool, nome: str):
    if clean:
        print(
            "Executando limpeza do Teste 2 (--clean): apenas output/teste2 (delivery preservada)"
        )
        limparTeste2(nome)

    print("=== TESTE 2.2 + 2.1 — Enriquecimento + Validação ===")
    csvFinal = executarEnriquecimentoEValidacao()
    print(f"Gerado: {csvFinal}")

    print("=== TESTE 2.3 — Agregação ===")
    csvAgregado, zipAgregado = executarAgregacaoAns(nome_zip=nome)
    print(f"Gerado CSV: {csvAgregado}")
    print(f"Gerado ZIP: {zipAgregado}")

    # Entrega (delivery/) — garantir que existe, mas NUNCA apagar
    deliveryDir = getDeliveryDir()
    deliveryDir.mkdir(parents=True, exist_ok=True)

    zipEntrega = deliveryDir / f"Teste_Agregacao_{nome}.zip"
    shutil.copyfile(zipAgregado, zipEntrega)

    print(f"Entrega gerada: {zipEntrega}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo do Teste 2 (2.2/2.1/2.3)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove apenas data/output/teste2 (preserva delivery/)",
    )
    parser.add_argument(
        "--nome",
        default="Gabriel_Martins",
        help="Nome usado no arquivo final de entrega (ex: Gabriel_Martins)",
    )

    args = parser.parse_args()
    main(clean=args.clean, nome=args.nome)
