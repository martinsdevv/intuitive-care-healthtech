import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
sys.path.insert(0, str(SRC))

import argparse
import shutil

from app.services.ans_consolidate import consolidarDespesas
from app.services.ans_download import executarDownloadAns
from app.services.ans_normalization import executarProcessamentoAns


def getRaizProjeto() -> Path:
    return Path(__file__).resolve().parents[2]


def limparDiretorios():
    raiz = getRaizProjeto()
    pastas = [
        raiz / "data/raw",
        raiz / "data/extracted",
        raiz / "data/staging",
        raiz / "data/output/teste1",
    ]

    for pasta in pastas:
        if pasta.exists():
            shutil.rmtree(pasta)
            print(f"Removido: {pasta}")


def main(clean: bool):
    if clean:
        print("Executando limpeza completa (--clean)")
        limparDiretorios()

    print("=== TESTE 1.1 — Download ===")
    executarDownloadAns()

    print("=== TESTE 1.2 — Normalização ===")
    executarProcessamentoAns()

    print("=== TESTE 1.3 — Consolidação ===")
    zipFinal = consolidarDespesas()

    print(f"Pipeline finalizado. Arquivo gerado: {zipFinal}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo do Teste 1"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove dados anteriores antes de executar o pipeline",
    )

    args = parser.parse_args()
    main(clean=args.clean)
