# Quickstart: reproducir el estudio y el modelo 1.1.0

## 1. Datos

```bash
make data           # dataset 2022–2025 (Open-Meteo, con caché y quality gates)
make data-holdout   # holdout 2026-01-01 → 2026-10-15, archivo aparte
```

## 2. Estudio (~1 h en 12 núcleos)

```bash
make study
```

Genera `reports/metrics/rain_classifier/study/study.json` y `reports/figures/study_*.png`: folds, candidatas (CV temporal y espacial), 68 ensayos de búsqueda, ablación, curva de aprendizaje, permutación, PDP/ICE, ciclo diurno, errores por segmento, calibración *cross-fitted*, curvas de costo y `decision_log`. Solo lee 2022–2024.

## 3. Modelo final y evaluación única

```bash
make train      # models/rain_classifier/1.1.0/ + reports/metrics/rain_classifier/1.1.0/metrics.json
make notebook   # notebooks/3.0-nm-evaluacion-y-calibracion.ipynb, leyendo solo reports/
```

## 4. Tests

```bash
make test
```

Incluye la corrida de punta a punta estudio → entrenamiento sobre datos sintéticos (`tests/test_predict.py`), la paridad de features 1.1.0 entre entrenamiento e inferencia (`tests/test_features.py`), la regla de un EE pareada (`tests/test_search.py`) y la model card regenerada igual a la versionada.

## Verificación registrada (2026-10-31)

- **Estudio** (`make study`, 50 min en 12 núcleos): ventana del pronóstico y ubicación adoptadas (aporte marginal > 1 EE pareado; la ubicación también mejora la CV espacial dejando una celda fuera); HGB elegido por la regla de 1 EE **pareada** (la versión no pareada eligió un modelo peor en todos los folds: hallazgo documentado en research R3); calibración Platt *cross-fitted* (ECE en desarrollo 0.027 → 0.004); ciclo diurno aprendido con máximo a las 14 h.
- **SC-002** ✅ configuración elegida frente a la 1.0.0 en la misma CV: Δ log loss −0.0037 ± 0.0026 (mejor en más de 1 EE pareado).
- **SC-003** ⚠️ ECE < 0.03 en desarrollo; en 2025 (0.057) y 2026 (0.039) no, por el cambio de tasa de lluvia entre años. Documentado en model card y README.
- **SC-004** ✅ holdout 2026 evaluado una sola vez en `make train`; `decision_log` sin decisiones sobre 2025/2026. El modelo 1.1.0 supera con IC pareado a climatología, pronóstico crudo, logística y al modelo 1.0.0 en 2025 y en 2026.
- **SC-005** ✅ estudio en 50 min.
- Stack completo con el modelo 1.1.0: `make smoke` en verde (Backend y routing envían el contrato 1.1.0: `clima_disponible=true`, heatmap de 81 puntos, planificar 201) y `make ui-smoke` en verde.
- `tests/test_predict.py` ejecuta estudio → entrenamiento → carga de punta a punta sobre datos sintéticos y verifica determinismo.
