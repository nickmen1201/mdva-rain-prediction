"""Carga segura del modelo de lluvia y predicción (contrato: specs/005-model-training/contracts/model-artifact.md)."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from mdva import config
from mdva.features import FEATURE_CONTRACT_VERSION, FEATURES, build_features

MODEL_NAME = "rain_classifier"


def model_dir(version: str, models_dir: Path | None = None) -> Path:
    return (models_dir or config.MODELS_DIR) / MODEL_NAME / version


class RainModel:
    def __init__(self, estimator, metadata: dict):
        self.estimator = estimator
        self.metadata = metadata
        self.amarillo = metadata["alert_thresholds"]["amarillo"]
        self.rojo = metadata["alert_thresholds"]["rojo"]

    def predict_proba(self, records: pd.DataFrame | list[dict]) -> np.ndarray:
        """Probabilidad calibrada de lluvia apreciable para cada registro (time_utc + 9 variables)."""
        return self.estimator.predict_proba(build_features(records))[:, 1]

    def alert_level(self, p: float) -> str:
        return "ROJO" if p > self.rojo else "AMARILLO" if p >= self.amarillo else "VERDE"


def load_model(version: str, models_dir: Path | None = None) -> RainModel:
    carpeta = model_dir(version, models_dir)
    metadata = json.loads((carpeta / "metadata.json").read_text(encoding="utf-8"))

    esperado = metadata["library_versions"]["scikit-learn"]
    if sklearn.__version__ != esperado:
        raise RuntimeError(
            f"El modelo {MODEL_NAME} {version} se entrenó con scikit-learn {esperado} "
            f"y el entorno tiene {sklearn.__version__}; cargarlo podría dar resultados inválidos."
        )
    if metadata["feature_contract_version"] != FEATURE_CONTRACT_VERSION or metadata["features"] != list(FEATURES):
        raise RuntimeError(
            f"El modelo usa el contrato de features {metadata['feature_contract_version']} y el código implementa "
            f"{FEATURE_CONTRACT_VERSION}; las features no coinciden."
        )
    return RainModel(joblib.load(carpeta / "model.joblib"), metadata)
