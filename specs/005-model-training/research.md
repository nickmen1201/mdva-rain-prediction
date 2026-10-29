# Research: Entrenamiento con validación temporal, baselines y calibración

## R1. Experimento exploratorio (2026-10-28)

Split de las Clarifications (entrenamiento 208 728 filas, validación 113 880, prueba 113 568; tasa de lluvia 19.2 % / 15.7 % / 21.5 %). Métricas en **validación** (2024), sin calibrar:

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | Tiempo | Tamaño |
|---|---|---|---|---|---|---|
| Climatología (hora local × mes) | 0.743 | 0.345 | 0.1209 | 0.3947 | — | — |
| Pronóstico crudo (logística sobre `precipitation_log1p`) | 0.741 | 0.361 | 0.1205 | 0.4002 | <1 s | — |
| Regresión logística (13 features, estandarizadas) | 0.817 | 0.472 | 0.1050 | 0.3441 | <1 s | <0.1 MB |
| HistGradientBoosting (300 it., lr 0.05) | **0.864** | **0.550** | **0.0947** | **0.3079** | 9 s | 1.1 MB |
| Random Forest (200 árboles, prof. 12) | 0.862 | 0.548 | 0.0955 | 0.3139 | 16 s | 30.2 MB |

Lecturas:
- El pronóstico crudo **no** supera a la climatología: el valor está en combinar variables, no en la precipitación pronosticada sola.
- HistGradientBoosting y Random Forest empatan en desempeño; HistGradientBoosting es 27 veces más liviano y cumple el límite de 5 MB (charter P7).

## R2. Candidatos y selección

- **Decision**: candidatos = regresión logística (baseline fuerte) e HistGradientBoosting con una rejilla pequeña (`learning_rate` ∈ {0.05, 0.1}, `max_leaf_nodes` ∈ {15, 31}, `max_iter` ∈ {200, 400}, `l2_regularization` ∈ {0, 1}; 16 combinaciones), `early_stopping=False` (la parada temprana interna de sklearn usa una partición aleatoria, que con datos horarios autocorrelacionados filtra información entre conjuntos). Selección por **log loss en validación**.
- **Rationale**: regla de puntuación propia, coherente con servir probabilidades. Random Forest queda fuera (empata y pesa 30 MB). Sin `class_weight`: el balanceo distorsiona las probabilidades (H-08).
- **Alternatives considered**: XGBoost/LightGBM (dependencias nuevas sin ganancia esperable frente a HistGradientBoosting); búsqueda bayesiana (fuera de alcance).

## R3. Calibración

- **Decision**: el modelo base se entrena en 2022–2023 y se congela (`sklearn.frozen.FrozenEstimator`); el calibrador (`CalibratedClassifierCV`) se ajusta sobre la validación 2024. El método (isotónica o sigmoide) se elige con un sub-split temporal de la validación (ajuste en enero–junio, evaluación en julio–diciembre, por log loss) y luego se reajusta en toda la validación.
- **Rationale**: así la elección del método no se evalúa con los mismos datos con que se ajusta, y 2025 queda intacto.
- **Riesgo conocido**: la tasa de lluvia de 2025 (21.5 %) difiere de la de 2024 (15.7 %); la calibración se reporta en prueba, no en validación.

## R4. Baselines

| Baseline | Definición | Desplegable |
|---|---|---|
| Climatología | tasa de lluvia de entrenamiento por (hora local, mes); si una celda no tiene datos, la tasa global | Sí |
| Pronóstico crudo | regresión logística sobre `precipitation_log1p` (convierte la precipitación pronosticada en probabilidad) | Sí |
| Regresión logística | 13 features estandarizadas | Sí |
| Persistencia | probabilidad = etiqueta de la hora anterior en la misma estación | **No** (la etiqueta es reanálisis, no existe en tiempo real); solo referencia |

## R5. Incertidumbre

- **Decision**: bootstrap en bloques de días (se remuestrean días UTC completos, con todas sus estaciones y horas), B = 500, semilla fija; IC 95 % por percentiles. Para SC-002 se calcula el IC de la **diferencia pareada** (modelo − baseline) dentro de cada réplica.
- **Rationale**: las horas de un mismo día y las estaciones de una misma celda están correlacionadas; el bootstrap por filas subestimaría la incertidumbre.

## R6. Métricas y niveles de alerta

- Error de calibración esperado: 10 intervalos de igual ancho, ponderado por número de predicciones.
- Niveles: VERDE p < 0.40, AMARILLO 0.40 ≤ p ≤ 0.70, ROJO p > 0.70 (charter RF-10). Se reportan la frecuencia de cada nivel, la tasa de lluvia observada dentro de cada nivel, y la precisión y sensibilidad de "≥ AMARILLO" y de "ROJO".

## R7. Validación externa

- **Decision**: probabilidades del modelo en las horas-estación de junio–julio de 2022 (excluidas del entrenamiento) frente a la lluvia medida por SIATA (horas válidas de `mdva.label_validation.siata_hourly`). ROC-AUC del modelo, del pronóstico crudo (como puntaje continuo) y de la precipitación de referencia; kappa del modelo al umbral AMARILLO.

## R8. Artefactos, seguimiento y carga segura

- `models/rain_classifier/<versión>/model.joblib` + `metadata.json` + `model_card.md` (versión 1.0.0).
- `reports/metrics/rain_classifier/<versión>/metrics.json` y figuras en `reports/figures/` (curva de confiabilidad, curvas PR).
- Registro de corrida: `reports/runs/<UTC>_<git-sha>.json` (parámetros, huella del dataset, versiones, métricas de validación y prueba).
- **Decision**: seguimiento con archivos JSON en el repo en lugar de MLflow.
- **Rationale**: cumple la constitución ("toda corrida registrada") sin servidor ni dependencia nueva; el historial queda en git.
- `mdva/modeling/predict.py` carga el modelo y **falla** si la versión de scikit-learn o la del contrato de features no coinciden con `metadata.json` (FR-009).
- **Nueva dependencia**: `matplotlib`, para las figuras del reporte; la stdlib no grafica.

## R9. Model card generada

- **Decision**: `mdva/modeling/model_card.py` produce `model_card.md` a partir de `metadata.json` y `metrics.json`; un test regenera la tarjeta y la compara con el archivo versionado (SC-004).

## R10. Calibración: corrección tras la primera corrida real (2026-10-28)

**Qué pasó.** La primera corrida con el diseño de R3 (calibrador sigmoide ajustado en 2024) dio en prueba ECE = 0.052 y probabilidad media 0.163 frente a una tasa observada de 0.215: el calibrador, ajustado en un año seco (15.7 %), subestimó la lluvia del año húmedo 2025. Al investigarlo, **se comparó una vez sobre el año de prueba** el efecto de tres estrategias (sin calibrar, calibración en 2024, calibración con validación cruzada por año). Esto viola el uso único de la prueba y se declara en la model card.

**Cómo se decidió sin depender de ese vistazo.** Se repitió la comparación usando solo datos de desarrollo, con 2024 como "prueba simulada" (modelo y calibradores ajustados en 2022–2023):

| Estrategia (evaluada en 2024) | Log loss | Brier | ECE |
|---|---|---|---|
| Base 2022 + calibración sigmoide en 2023 | 0.3275 | 0.1007 | 0.0221 |
| Base 2022 + calibración isotónica en 2023 | 0.3286 | 0.1004 | 0.0172 |
| Validación cruzada por año 2022–2023 (sigmoide) | 0.3151 | 0.0961 | 0.0338 |
| Validación cruzada por año 2022–2023 (isotónica) | 0.3155 | 0.0958 | 0.0279 |
| **Base 2022–2023 sin calibración posterior** | **0.3066** | **0.0945** | **0.0162** |

- **Decision**: el procedimiento de R3 agrega "sin calibración" como tercera opción, elegida igual que las otras: menor log loss en julio–diciembre de 2024. HistGradientBoosting optimiza log loss y sus probabilidades nativas ya están calibradas; recalibrar con un solo año de tasa distinta traslada ese sesgo de tasa.
- **Consecuencia esperada**: el cambio de tasa entre años (16 % → 22 %) seguirá afectando la calibración en 2025 con cualquier estrategia; SC-003 puede no cumplirse y, si no se cumple, se reporta así.
