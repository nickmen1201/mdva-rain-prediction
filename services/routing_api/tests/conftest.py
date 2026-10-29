import sys
from pathlib import Path

# Los módulos del servicio (domain, application, ...) se importan desde services/routing_api/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
