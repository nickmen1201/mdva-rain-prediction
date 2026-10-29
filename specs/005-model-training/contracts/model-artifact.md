# Contract: artefacto del modelo `rain_classifier`

Consumidores: `mdva.modeling.predict` (spec 005) y el ML API (spec 006).

## Archivos

```text
models/rain_classifier/<version>/
├── model.joblib     # estimador de scikit-learn: el base o CalibratedClassifierCV(FrozenEstimator(base))
├── metadata.json
└── model_card.md    # generado por mdva.modeling.model_card
```

## `metadata.json`

| Campo | Tipo | Descripción |
|---|---|---|
| `model_name` | str | `"rain_classifier"` |
| `model_version` | str (SemVer) | versión del artefacto |
| `created_at_utc` | str ISO 8601 | fecha de entrenamiento |
| `git_sha` | str | commit del código que entrenó |
| `dataset_contract_version` | str | versión del contrato `rain_hourly` |
| `dataset_fingerprint` | str | huella de contenido del dataset |
| `feature_contract_version` | str | versión del contrato de features |
| `features` | list[str] | nombres en orden |
| `label` | obj | `{"threshold_mm": float, "source": "ERA5"}` |
| `splits` | obj | `{train, validation, test, external}` → `{start, end, rows, rain_rate}`; `train.excluded` |
| `base_estimator` | obj | `{"class": str, "params": obj}` |
| `calibration` | obj | `{"method": "none" \| "isotonic" \| "sigmoid", "fitted_on": "validation" \| null}` |
| `alert_thresholds` | obj | `{"amarillo": 0.40, "rojo": 0.70}` |
| `seed` | int | semilla |
| `library_versions` | obj | `{python, scikit-learn, numpy, pandas}` |
| `size_bytes` | int | tamaño de `model.joblib` |
| `metrics_path` | str | ruta del reporte de métricas |

## Interfaz de predicción (`mdva.modeling.predict`)

```python
model = load_model(version="1.0.0")   # RuntimeError si scikit-learn o el contrato de features no coinciden
model.predict_proba(records)          # records: list[dict] | DataFrame con time_utc + 9 variables (spec 004)
                                      # → numpy array de probabilidades calibradas, en [0, 1]
model.alert_level(p)                  # "VERDE" | "AMARILLO" | "ROJO"
model.metadata                        # dict de metadata.json
```

Errores: `FeatureInputError` (entradas inválidas, spec 004) y `RuntimeError` (incompatibilidad de versiones).
