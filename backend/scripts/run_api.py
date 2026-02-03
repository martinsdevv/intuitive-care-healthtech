import os
import subprocess
import sys

os.environ["PYTHONPATH"] = "backend/src"

subprocess.run(
    [sys.executable, "-m", "uvicorn", "app.api.main:app", "--reload", "--port", "8000"],
    check=True,
)
