import sys
from pathlib import Path

# adiciona backend/src ao PYTHONPATH
root = Path(__file__).resolve().parents[1]
srcPath = root / "src"

sys.path.insert(0, str(srcPath))
