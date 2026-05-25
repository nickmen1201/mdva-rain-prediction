"""
Entrena el modelo de intensidad de lluvia (regressor) para el routing service.
Script equivalente a ../train_rain_model.py — ejecutar desde este directorio.
"""
import sys
from pathlib import Path

# Delegar al script raíz del módulo
sys.path.insert(0, str(Path(__file__).parent.parent))
from train_rain_model import train_model

if __name__ == "__main__":
    train_model()
