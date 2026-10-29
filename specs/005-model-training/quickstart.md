# Quickstart: validar el entrenamiento

```bash
make data          # spec 003 (si no existe el dataset)
make train         # = uv run python -m mdva.modeling.train
make test
```

Esperado:
- `models/rain_classifier/1.0.0/` con `model.joblib` (< 5 MB), `metadata.json` y `model_card.md`;
- `reports/metrics/rain_classifier/1.0.0/metrics.json` con validación y prueba para `model`, `climatology`, `raw_forecast`, `logistic`, `persistence_reference`, IC 95 %, confiabilidad, niveles de alerta y validación externa;
- `claims.beats_climatology` y `claims.beats_raw_forecast` en `true` y `claims.ece_below_0_03` en `true` (o explicados en la model card);
- un nuevo `reports/runs/*.json`.

Determinismo (SC-001):

```bash
make train && cp reports/metrics/rain_classifier/1.0.0/metrics.json /tmp/m1.json
make train && diff <(jq -S 'del(.created_at_utc)' /tmp/m1.json) <(jq -S 'del(.created_at_utc)' reports/metrics/rain_classifier/1.0.0/metrics.json)
```

Carga segura:

```python
from mdva.modeling.predict import load_model
m = load_model("1.0.0")
m.predict_proba([{"time_utc": "2026-10-28T20:00:00Z", "temperature_2m": 19.0, "relative_humidity_2m": 85,
                  "dew_point_2m": 16.4, "cloud_cover": 90, "wind_speed_10m": 2.0, "wind_direction_10m": 180,
                  "pressure_msl": 1013, "precipitation": 0.4, "cape": 300}])
```

## Verificación registrada (2026-10-28)

- Modelo elegido: HistGradientBoosting (`learning_rate` 0.1, `max_leaf_nodes` 15, `max_iter` 400, `l2_regularization` 1.0), sin calibración posterior (elegida en validación: log loss 0.3246 frente a 0.3259 sigmoide y 0.3291 isotónica). 0.74 MB.
- **SC-001** ✅ dos ejecuciones → `metrics.json` idéntico byte a byte.
- **SC-002** ✅ en prueba (2025) el modelo supera a la climatología (ΔBrier −0.0135 [−0.0174, −0.0093]), al pronóstico crudo (−0.0294 [−0.0329, −0.0258]) y a la regresión logística (−0.0095 [−0.0125, −0.0068]); también en log loss. ROC-AUC 0.825 [0.810, 0.840].
- **SC-003** ❌ ECE en prueba 0.0346 (meta < 0.03). El modelo subestima de forma sistemática en 2025 (probabilidad media 0.180 frente a una tasa de 0.215), por el cambio de tasa de lluvia entre años. Documentado en la model card y en research R10.
- **SC-004** ✅ `tests/test_model_card.py` regenera la tarjeta y coincide.
- **SC-005** ✅ 0.74 MB.
- Validación externa (pluviómetros SIATA, jun–jul 2022): ROC-AUC del modelo 0.509, del pronóstico crudo 0.536 y de la etiqueta ERA5 0.532 → ninguna fuente de malla predice la lluvia horaria **en un punto**; el modelo predice la lluvia de la celda.
