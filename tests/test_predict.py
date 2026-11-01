"""Estudio + entrenamiento de punta a punta con datos sintéticos, carga segura y determinismo (specs 005 y 012)."""

import json

import numpy as np
import pandas as pd
import pytest

from mdva.features import FEATURES, RAW_INPUTS
from mdva.modeling import predict, study, train

ESTACIONES = {59: (6.25, -75.57, "6.25,-75.5"), 60: (6.15, -75.62, "6.15,-75.75")}


def _serie(inicio, fin, rng):
    t = pd.date_range(inicio, fin, freq="h", tz="UTC")
    partes = []
    for sid, (lat, lon, celda) in ESTACIONES.items():
        n = len(t)
        precip = rng.exponential(0.3, n)
        nubes = rng.uniform(40, 100, n)
        # La lluvia depende de la precipitación de la hora y de la siguiente (señal de la ventana)
        logit = -3 + 4 * np.log1p(precip) + 3 * np.log1p(np.roll(precip, -1)) + (nubes - 70) / 15 + (lat - 6.2) * 5
        rain = rng.uniform(size=n) < 1 / (1 + np.exp(-logit))
        partes.append(
            pd.DataFrame(
                {
                    "station_id": np.int64(sid),
                    "time_utc": t,
                    "latitude": lat,
                    "longitude": lon,
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
                    "era5_cell": celda,
                    "rain": rain,
                }
            )
        )
    return pd.concat(partes, ignore_index=True)


@pytest.fixture(scope="module")
def sintetico():
    rng = np.random.default_rng(0)
    return _serie("2022-01-01", "2025-12-31 23:00", rng), _serie("2026-01-01", "2026-03-31 23:00", rng)


@pytest.fixture(scope="module")
def entrenado(sintetico, tmp_path_factory):
    principal, fresco = sintetico
    raiz = tmp_path_factory.mktemp("artefactos")
    resultado = study.run(principal, quick=True)
    study.write(resultado, out_dir=raiz / "study", figures_dir=raiz / "reports" / "figures")
    estudio = json.loads((raiz / "study" / "study.json").read_text(encoding="utf-8"))
    # Con 2 celdas la validación espacial no puede respaldar la ubicación; el entrenamiento se prueba
    # con el contrato completo (las decisiones reales salen del estudio sobre el dataset real)
    estudio["feature_set"]["features"] = list(FEATURES)
    externos = principal[(principal.time_utc >= "2022-06-07") & (principal.time_utc < "2022-07-07")]
    siata = externos[["station_id", "time_utc"]].assign(rain_obs=externos["rain"].to_numpy())
    r = train.run(
        principal,
        fresco,
        study=estudio,
        n_boot=20,
        siata_hours=siata,
        out_models=raiz / "models",
        out_reports=raiz / "reports",
        compare_previous=False,
    )
    return r, raiz, estudio, siata


def test_estudio_completo(entrenado):
    _, raiz, estudio, _ = entrenado
    assert [f["name"] for f in estudio["folds"]] == ["2023-T3", "2023-T4", "2024-T1", "2024-T2", "2024-T3", "2024-T4"]
    assert estudio["feature_candidates"]["marginal"]["window|base"]["better_by_1se"]  # la señal sintética usa t+1
    assert {"hgb", "spline_logistic", "random_forest"} <= {t["family"] for t in estudio["search"]["trials"]}
    assert estudio["calibration"]["chosen"] in {"none", "isotonic", "sigmoid"}
    assert estudio["decision_log"] and estudio["permutation_importance"]
    assert (raiz / "reports" / "figures" / "study_ablation.png").exists()


def test_artefactos_completos(entrenado):
    r, raiz, _, _ = entrenado
    carpeta = raiz / "models" / "rain_classifier" / train.MODEL_VERSION
    assert {p.name for p in carpeta.iterdir()} == {"model.joblib", "metadata.json", "model_card.md"}
    meta = json.loads((carpeta / "metadata.json").read_text(encoding="utf-8"))
    assert meta["features"] == list(FEATURES) and meta["feature_contract_version"] == "1.1.0"
    assert meta["size_bytes"] < 5_000_000
    assert (raiz / "reports" / "figures" / "rain_classifier_reliability.png").exists()
    assert len(list((raiz / "reports" / "runs").glob("*.json"))) == 1
    splits = r["metrics"]["splits"]
    assert set(splits) == {"test_2025", "holdout_2026"}
    assert set(splits["holdout_2026"]["models"]) == {
        "model",
        "climatology",
        "raw_forecast",
        "logistic",
        "persistence_reference",
    }
    assert splits["holdout_2026"]["period"][0].startswith("2026-01-02")  # hueco de 24 h tras desarrollo/prueba
    assert splits["test_2025"]["claims"]["beats_climatology"]  # la señal sintética es fuerte
    assert "Holdout fresco 2026" in (carpeta / "model_card.md").read_text(encoding="utf-8")


def test_entrenamiento_determinista(sintetico, entrenado, tmp_path):
    r1, _, estudio, siata = entrenado
    principal, fresco = sintetico
    r2 = train.run(
        principal,
        fresco,
        study=estudio,
        n_boot=20,
        siata_hours=siata,
        out_models=tmp_path / "m",
        out_reports=tmp_path / "r",
        compare_previous=False,
    )
    assert r1["metrics"] == r2["metrics"]


def test_carga_y_prediccion(entrenado):
    _, raiz, _, _ = entrenado
    m = predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")
    registro = {"time_utc": "2025-10-28T20:00:00Z", **{k: (c.min + c.max) / 2 for k, c in RAW_INPUTS.items()}}
    p = m.predict_proba([registro])
    assert p.shape == (1,) and 0.0 <= p[0] <= 1.0
    assert m.alert_level(0.39) == "VERDE" and m.alert_level(0.40) == "AMARILLO" and m.alert_level(0.71) == "ROJO"


def test_version_de_scikit_learn_distinta_falla(entrenado, monkeypatch):
    _, raiz, _, _ = entrenado
    monkeypatch.setattr(predict.sklearn, "__version__", "0.0.1")
    with pytest.raises(RuntimeError, match="scikit-learn"):
        predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")


def test_contrato_de_features_distinto_falla(entrenado, monkeypatch):
    _, raiz, _, _ = entrenado
    monkeypatch.setattr(predict, "FEATURE_CONTRACT_VERSION", "9.9.9")
    with pytest.raises(RuntimeError, match="contrato de features"):
        predict.load_model(train.MODEL_VERSION, models_dir=raiz / "models")


def test_estudio_que_no_coincide_con_el_contrato_falla(sintetico):
    with pytest.raises(RuntimeError, match="contrato"):
        train.run(sintetico[0], study={"feature_set": {"features": ["otra"]}})
