"""Entrenamiento de punta a punta con datos sintéticos, carga segura y determinismo."""

import json

import numpy as np
import pandas as pd
import pytest

from mdva.features import RAW_INPUTS
from mdva.modeling import predict, train


@pytest.fixture(scope="module")
def sintetico():
    rng = np.random.default_rng(0)
    t = pd.date_range("2022-01-01", "2025-12-31 23:00", freq="3h", tz="UTC")
    n = len(t)
    precip = rng.exponential(0.3, n)
    nubes = rng.uniform(40, 100, n)
    logit = -3 + 2.5 * np.log1p(precip) * 3 + (nubes - 70) / 15
    rain = rng.uniform(size=n) < 1 / (1 + np.exp(-logit))
    return pd.DataFrame(
        {
            "station_id": np.int64(59),
            "time_utc": t,
            "temperature_2m": rng.uniform(14, 28, n),
            "relative_humidity_2m": rng.uniform(50, 100, n),
            "dew_point_2m": rng.uniform(8, 18, n),
            "cloud_cover": nubes,
            "wind_speed_10m": rng.uniform(0, 4, n),
            "wind_direction_10m": rng.uniform(0, 360, n),
            "pressure_msl": rng.uniform(1008, 1020, n),
            "precipitation": precip,
            "cape": rng.exponential(150, n),
            "precipitation_ref": np.where(rain, 1.0, 0.0),
            "era5_cell": "6.25,-75.5",
            "rain": rain,
        }
    )


@pytest.fixture(scope="module")
def entrenado(sintetico, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("artefactos")
    externos = sintetico[(sintetico.time_utc >= "2022-06-07") & (sintetico.time_utc < "2022-07-07")]
    siata = externos[["station_id", "time_utc"]].assign(rain_obs=externos["rain"].to_numpy())
    r = train.run(sintetico, n_boot=20, siata_hours=siata, out_models=raiz / "models", out_reports=raiz / "reports")
    return r, raiz


def test_artefactos_completos(entrenado):
    r, raiz = entrenado
    carpeta = raiz / "models" / "rain_classifier" / train.MODEL_VERSION
    assert {p.name for p in carpeta.iterdir()} == {"model.joblib", "metadata.json", "model_card.md"}
    meta = json.loads((carpeta / "metadata.json").read_text(encoding="utf-8"))
    assert meta["features"] and meta["calibration"]["method"] in {"none", "isotonic", "sigmoid"}
    assert meta["size_bytes"] < 5_000_000
    assert (raiz / "reports" / "figures" / "rain_classifier_reliability.png").exists()
    assert len(list((raiz / "reports" / "runs").glob("*.json"))) == 1
    metrics = r["metrics"]
    assert set(metrics["splits"]["test"]["models"]) == {
        "model",
        "climatology",
        "raw_forecast",
        "logistic",
        "persistence_reference",
    }
    assert len(metrics["selection"]["candidates"]) == 17
    assert metrics["claims"]["beats_climatology"]  # la señal sintética es fuerte


def test_entrenamiento_determinista(sintetico, entrenado, tmp_path):
    r1, _ = entrenado
    externos = sintetico[(sintetico.time_utc >= "2022-06-07") & (sintetico.time_utc < "2022-07-07")]
    siata = externos[["station_id", "time_utc"]].assign(rain_obs=externos["rain"].to_numpy())
    r2 = train.run(sintetico, n_boot=20, siata_hours=siata, out_models=tmp_path / "m", out_reports=tmp_path / "r")
    assert r1["metrics"] == r2["metrics"]


def test_carga_y_prediccion(entrenado):
    _, raiz = entrenado
    m = predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")
    registro = {"time_utc": "2025-10-28T20:00:00Z", **{k: (c.min + c.max) / 2 for k, c in RAW_INPUTS.items()}}
    p = m.predict_proba([registro])
    assert p.shape == (1,) and 0.0 <= p[0] <= 1.0
    assert m.alert_level(0.39) == "VERDE" and m.alert_level(0.40) == "AMARILLO" and m.alert_level(0.71) == "ROJO"


def test_version_de_scikit_learn_distinta_falla(entrenado, monkeypatch):
    _, raiz = entrenado
    monkeypatch.setattr(predict.sklearn, "__version__", "0.0.1")
    with pytest.raises(RuntimeError, match="scikit-learn"):
        predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")


def test_contrato_de_features_distinto_falla(entrenado, monkeypatch):
    _, raiz = entrenado
    monkeypatch.setattr(predict, "FEATURE_CONTRACT_VERSION", "9.9.9")
    with pytest.raises(RuntimeError, match="contrato de features"):
        predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")
