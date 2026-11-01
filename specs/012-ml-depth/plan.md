# Implementation Plan: Profundidad de ML

**Branch**: `012-ml-depth` (trabajo directo en `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

## Summary

Un estudio reproducible (`make study` → `mdva.modeling.study`) toma todas las decisiones con CV temporal *rolling origin* dentro de 2022–2024: features candidatas (con validación espacial para la ubicación), búsqueda de hiperparámetros (60 HGB + logística con *splines* + bosque aleatorio, regla de 1 EE), ablación, curva de aprendizaje, permutación con IC, PDP/ICE, errores por segmento, calibración con *cross-fitting* y curvas de costo. `make train` lee `study.json`, entrena `rain_classifier` 1.1.0 en todo desarrollo con la calibración elegida (mapa ajustado sobre las predicciones *out-of-fold*), y lo evalúa **una vez** en 2025 y en el holdout fresco 2026 (`make data-holdout`) contra baselines y contra 1.0.0. Si el estudio adopta features nuevas, el contrato de features pasa a 1.1.0 y el ML API, el Backend y el routing service envían las entradas nuevas desde la misma respuesta de Open-Meteo.

## Technical Context

**Language/Version**: Python 3.11 (`mdva`, ML API, routing service), Java 21 (Backend).

**Primary Dependencies**: scikit-learn 1.8.0 (búsqueda, `permutation_importance`, `partial_dependence`, `SplineTransformer`, `IsotonicRegression`), matplotlib (figuras), `nbformat`/`nbclient` para ejecutar el notebook en CI local (dependencia de desarrollo; justificación: ejecutar el notebook 3.0 de forma reproducible sin Jupyter interactivo). Sin Optuna ni SHAP (la stdlib + scikit-learn bastan; constitución).

**Testing**: pytest (`tests/test_cv.py`, `test_search.py`, `test_analysis.py`, `test_candidates.py`, `test_features.py` ampliado, test de paridad del contrato 1.1.0); tests del ML API (contrato OpenAPI), del routing service y del Backend para las entradas nuevas.

**Performance Goals**: estudio completo < 60 min en 12 núcleos (SC-005); cada ajuste de HGB ≈ 7 s.

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| VI. Evaluación honesta | CV temporal con hueco; 2025 y 2026 fuera de toda decisión; `decision_log`; holdout evaluado una vez; IC por bootstrap en bloques de días. | ✅ |
| VI. Paridad train/serve | Las features nuevas son del **mismo** pronóstico horario disponible en producción; un único `build_features` (contrato 1.1.0) para entrenar y servir; test de paridad. Sin rellenos: faltar una entrada nueva → 422. | ✅ |
| VI. Probabilidades calibradas | Calibración elegida por *cross-fitting*; ECE reportado en desarrollo, 2025 y 2026. | ✅ |
| IV. Contract-first | `contracts/features.v1.1.md` y `openapi-v2.yaml` actualizado (cambio **rompiente** de entrada para el ML API v2, coordinado con sus dos consumidores en la misma spec; se documenta el diff). | ✅ |
| II/P7. Reproducible, artefactos | Semillas fijas; modelo < 5 MB versionado con `metadata.json` y model card; datos fuera de git. | ✅ |

## Project Structure

```text
mdva/modeling/cv.py, search.py, analysis.py, candidates.py → study.py   # estudio (nuevo)
mdva/features.py                     # contrato 1.1.0 (ventana del pronóstico + ubicación) si se adoptan
mdva/modeling/train.py               # 1.1.0 desde study.json; evaluación 2025 + holdout 2026; decision_log
mdva/modeling/model_card.py          # secciones nuevas
mdva/dataset.py, openmeteo.py, config.py  # holdout 2026 en archivo aparte
mdva/plots.py                        # figuras del estudio
notebooks/3.0-nm-evaluacion-y-calibracion.ipynb
services/ml_api/v2.py + contracts    # entradas nuevas
apps/backend/.../weather/HourlyInputs.java, OpenMeteoForecastClient.java   # ventana + ubicación
services/routing_api/infrastructure/rain_signal.py, rain_grid.py           # ídem
Makefile                             # study, data-holdout, notebook
```

## Complexity Tracking

| Violación | Por qué se necesita | Alternativa más simple descartada |
|---|---|---|
| Cambio rompiente del contrato de entrada del ML API v2 | Las features adoptadas mejoran el log loss en > 1 EE y requieren entradas nuevas | Mantener v2 sin ellas: deja desempeño medido sobre la mesa; versionar `/v3` duplicaría el servicio para dos consumidores internos que se actualizan en la misma spec |
