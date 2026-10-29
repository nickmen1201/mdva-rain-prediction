# Implementation Plan: Entrenamiento con validación temporal, baselines y calibración

**Branch**: `005-model-training` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-model-training/spec.md`

## Summary

`python -m mdva.modeling.train` reemplaza el script heredado: construye features con `mdva.features`, divide en el tiempo (2022–23 / 2024 / 2025, junio–julio de 2022 reservados para la validación externa), elige entre regresión logística e HistGradientBoosting (rejilla de 16) por log loss en validación, calibra sobre 2024 (método elegido con un sub-split temporal), evalúa una vez en 2025 frente a climatología, pronóstico crudo, logística y persistencia (referencia), con bootstrap por días, y guarda el modelo (< 5 MB, en git) con metadatos, model card generada, figuras y registro de corrida. `mdva.modeling.predict` carga el modelo verificando versiones.

## Technical Context

**Language/Version**: Python 3.11 (paquete `mdva`)

**Primary Dependencies**: scikit-learn 1.8.0 (`HistGradientBoostingClassifier`, `CalibratedClassifierCV`, `FrozenEstimator`), pandas, numpy, joblib. Nueva: `matplotlib` (figuras; R8).

**Storage**: `models/rain_classifier/1.0.0/` (versionado), `reports/` (versionado)

**Testing**: pytest con datos sintéticos (splits, baselines, métricas, bootstrap por bloques, carga con versión incompatible, sincronía de la model card)

**Target Platform**: local; CI corre los tests sin dataset real

**Project Type**: pipeline de ML en el paquete CCDS v2

**Performance Goals**: entrenamiento + evaluación completos en < 15 min en un portátil

**Constraints**: prueba usada una sola vez; determinista; modelo < 5 MB

**Scale/Scope**: 456 k filas; 16 + 1 candidatos; 5 modelos evaluados

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| II. Reproducible | Un comando; semilla fija; huella del dataset en metadatos; prueba de determinismo (SC-001). | ✅ |
| IV. Contract-first | [contracts/model-artifact.md](contracts/model-artifact.md) define metadata y la interfaz de predicción que consumirá el ML API. | ✅ |
| VI. Evaluación honesta | Holdout temporal; baselines definidos; métricas propias; IC por bloques; calibración medida en prueba; registro de corridas; versiones verificadas al cargar. | ✅ |
| VII. Sin datos fabricados | Persistencia marcada como no desplegable; sin `class_weight`. | ✅ |
| Notebooks no en producción | Todo el pipeline en `mdva/modeling/`. | ✅ |
| Dependencias justificadas | `matplotlib` (R8); sin MLflow (R8). | ✅ |

**Post-design re-check**: sin violaciones.

## Project Structure

```text
specs/005-model-training/{plan.md, research.md, data-model.md, quickstart.md, tasks.md, contracts/model-artifact.md}
mdva/modeling/
├── splits.py        # máscaras temporales
├── baselines.py     # climatología, pronóstico crudo, persistencia
├── evaluate.py      # métricas, ECE, confiabilidad, bootstrap por días, niveles, validación externa
├── train.py         # CLI: selección, calibración, evaluación, artefactos, registro de corrida (reemplaza el script heredado)
├── predict.py       # carga segura + predict_proba + alert_level
└── model_card.py    # model_card.md desde metadata + métricas
mdva/plots.py        # curva de confiabilidad y curvas PR
tests/test_splits.py, test_baselines.py, test_evaluate.py, test_predict.py, test_model_card.py
models/rain_classifier/1.0.0/{model.joblib, metadata.json, model_card.md}
reports/metrics/rain_classifier/1.0.0/metrics.json, reports/figures/*.png, reports/runs/*.json
Makefile: train
```

**Structure Decision**: submódulos de `mdva/modeling/` según la plantilla CCDS v2 (`train.py`, `predict.py`) más `evaluate.py`, `baselines.py` y `splits.py` para poder probarlos por separado.

## Complexity Tracking

Sin violaciones.
