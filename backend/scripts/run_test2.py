import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
sys.path.insert(0, str(SRC))

import argparse
import shutil

from app.core.paths import DELIVERY_DIR, OUTPUT_TESTE2_DIR
from app.usecases.ans_agregate import executarAgregacaoAns
from app.usecases.ans_enrich_validate import executarEnriquecimentoEValidacao


def limparTeste2(nome: str):
    # apaga somente outputs do teste 2
    if OUTPUT_TESTE2_DIR.exists():
        shutil.rmtree(OUTPUT_TESTE2_DIR)
        print(f"Removido: {OUTPUT_TESTE2_DIR}")

    # opcional: apaga só o zip de entrega específico, sem apagar a pasta delivery
    entrega = DELIVERY_DIR / f"Teste_Agregacao_{nome}.zip"
    if entrega.exists():
        entrega.unlink()
        print(f"Removido: {entrega}")


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
    print(f"Gerado ZIP (output): {zipAgregado}")

    # entrega: runner é o único responsável por delivery/
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    zipEntrega = DELIVERY_DIR / f"Teste_Agregacao_{nome}.zip"
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
        help="Nome usado no arquivo final (ex: Gabriel_Martins)",
    )
    args = parser.parse_args()

    main(clean=args.clean, nome=args.nome)
