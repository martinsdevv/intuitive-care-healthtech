from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
STAGING_DIR = DATA_DIR / "staging"

OUTPUT_DIR = DATA_DIR / "output"
OUTPUT_TESTE1_DIR = OUTPUT_DIR / "teste1"
OUTPUT_TESTE2_DIR = OUTPUT_DIR / "teste2"

DELIVERY_DIR = ROOT / "delivery"
DOCS_DIR = ROOT / "docs"
DB_DIR = ROOT / "db"
