import sys
from pathlib import Path

# main.py vive en services/ml_api/ y no es un paquete instalable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
