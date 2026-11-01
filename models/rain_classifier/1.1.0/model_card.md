# Model card — rain_classifier 1.1.0

> Generada automáticamente por `mdva.modeling.model_card` desde `metadata.json`, `reports/metrics/rain_classifier/1.1.0/metrics.json`
> y `reports/metrics/rain_classifier/study/study.json`. No editar a mano.

## Qué predice

Probabilidad calibrada de que en la celda de reanálisis ERA5 que contiene un punto del Valle de Aburrá caiga lluvia
apreciable (≥ 0.5 mm) en una hora dada, a partir del pronóstico horario de Open-Meteo
para ese punto (24 features, contrato v1.1.0: variables de la
hora, ventana t−2…t+2 del mismo pronóstico y ubicación; ver `docs/features.md`).

**Uso previsto**: alertas de lluvia para planificar trayectos (VERDE < 0.4,
AMARILLO ≤ 0.7, ROJO > 0.7).
**No** es un pronóstico de intensidad ni de lluvia medida en un punto exacto.

## Modelo

- **HistGradientBoosting** `{'learning_rate': 0.097271, 'max_leaf_nodes': 29, 'min_samples_leaf': 200, 'l2_regularization': 0.04605, 'max_features': 0.520807, 'max_iter': 159}`.
- Elegido con validación cruzada temporal *rolling origin* (6 folds trimestrales 2023-T3 → 2024-T4,
  ventana creciente, hueco de 24 h) entre 67 configuraciones (60 HGB por
  búsqueda aleatoria + familias de referencia), con la **regla de un error estándar** (la más simple a ≤ 1 EE de la mejor).
- Frente a la configuración 1.0.0 en la misma CV: Δ log loss -0.0037 ± 0.0026
  (mejora en más de 1 EE).
- Calibración: `sigmoid`, mapa ajustado sobre predicciones out-of-fold de desarrollo (cross-fitting).
- Tamaño: 0.25 MB · scikit-learn 1.8.0 · semilla 42.

| Familia (mejor configuración) | Log loss CV (media ± EE) | ROC-AUC CV | Hiperparámetros |
|---|---|---|---|
| HistGradientBoosting | 0.2924 ± 0.0381 | 0.869 | `{'learning_rate': 0.045183, 'max_leaf_nodes': 20, 'min_samples_leaf': 100, 'l2_regularization': 6.64497, 'max_features': 0.643223, 'max_iter': 564}` |
| Logística con *splines* (GAM) | 0.3120 ± 0.0402 | 0.845 | `{'n_knots': 6, 'C': 0.1}` |
| Bosque aleatorio | 0.3018 ± 0.0374 | 0.867 | `{'max_depth': None, 'min_samples_leaf': 20}` |
| HGB con la configuración 1.0.0 | 0.2964 ± 0.0380 | 0.864 | `{'learning_rate': 0.1, 'max_leaf_nodes': 15, 'max_iter': 400, 'l2_regularization': 1.0, 'max_features': 1.0, 'min_samples_leaf': 20}` |

Sensibilidad por hiperparámetro: `reports/figures/study_hgb_sensitivity.png`.

## Datos

| Periodo | Rango (UTC) | Filas | Tasa de lluvia | Uso |
|---|---|---|---|---|
| Desarrollo | 2022-01-01 → 2024-12-31 (sin jun–jul 2022) | 322,894 | 18.0 % | todas las decisiones (CV) y el ajuste final |
| Prueba 2025 | 2025-01-02 → 2025-12-31 | 113,568 | 21.5 % | evaluación (ya usada para reportar 1.0.0) |
| Holdout 2026 | 2026-01-02 → 2026-10-15 | 89,518 | 16.3 % | evaluación única, nunca vista |

13 estaciones SIATA como ubicaciones (5 celdas ERA5). Huella del dataset: `57133164d885fd2e…`.

## Holdout fresco 2026 (nunca usado en ninguna decisión)

Periodo 2026-01-02 → 2026-10-15 · 89,518 horas-estación · llueve en el 16.3 %. IC 95 % por bootstrap en bloques de días (B = 500).

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | BSS vs climatología | ECE |
|---|---|---|---|---|---|---|
| **Modelo 1.1.0** | 0.837 [0.820, 0.856] | 0.525 | 0.1049 [0.092, 0.118] | 0.342 | 0.151 | 0.0389 |
| Modelo 1.0.0 (spec 005) | 0.805 [0.789, 0.824] | 0.488 | 0.1087 [0.096, 0.121] | 0.356 | 0.120 | 0.0206 |
| Regresión logística | 0.799 [0.779, 0.820] | 0.469 | 0.1098 [0.098, 0.121] | 0.359 | 0.111 | 0.0169 |
| Pronóstico crudo | 0.714 [0.698, 0.733] | 0.346 | 0.1251 [0.113, 0.138] | 0.411 | -0.013 | 0.0279 |
| Climatología | 0.724 [0.694, 0.754] | 0.362 | 0.1235 [0.110, 0.138] | 0.403 | 0.000 | 0.0382 |
| Persistencia (no desplegable) | 0.806 [0.793, 0.821] | 0.510 | 0.1054 [0.097, 0.115] | 1.457 | 0.146 | 0.1055 |

Diferencias pareadas (modelo − baseline; IC 95 % < 0 en Brier y log loss = supera):
- vs Modelo 1.0.0 (spec 005): **supera** (Δ Brier -0.0038 [-0.005, -0.002])
- vs Regresión logística: **supera** (Δ Brier -0.0049 [-0.008, -0.002])
- vs Pronóstico crudo: **supera** (Δ Brier -0.0204 [-0.023, -0.018])
- vs Climatología: **supera** (Δ Brier -0.0188 [-0.024, -0.014])

| Nivel de alerta | % de horas | Llueve dentro del nivel |
|---|---|---|
| VERDE | 91.3 % | 11.8 % |
| AMARILLO | 6.8 % | 60.2 % |
| ROJO | 1.9 % | 75.3 % |

Alerta ≥ AMARILLO: precisión 0.636, sensibilidad 0.339 · ROJO: precisión 0.753, sensibilidad 0.089.

## Desempeño en prueba 2025

Periodo 2025-01-02 → 2025-12-31 · 113,568 horas-estación · llueve en el 21.5 %. IC 95 % por bootstrap en bloques de días (B = 500).

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | BSS vs climatología | ECE |
|---|---|---|---|---|---|---|
| **Modelo 1.1.0** | 0.846 [0.830, 0.860] | 0.615 | 0.1234 [0.113, 0.134] | 0.393 | 0.113 | 0.0572 |
| Modelo 1.0.0 (spec 005) | 0.825 [0.810, 0.840] | 0.581 | 0.1264 [0.116, 0.137] | 0.401 | 0.091 | 0.0346 |
| Regresión logística | 0.805 [0.789, 0.822] | 0.545 | 0.1323 [0.121, 0.143] | 0.417 | 0.049 | 0.0312 |
| Pronóstico crudo | 0.702 [0.688, 0.716] | 0.398 | 0.1567 [0.145, 0.169] | 0.489 | -0.126 | 0.0422 |
| Climatología | 0.777 [0.753, 0.797] | 0.505 | 0.1391 [0.126, 0.152] | 0.439 | 0.000 | 0.0369 |
| Persistencia (no desplegable) | 0.815 [0.804, 0.826] | 0.566 | 0.1247 [0.118, 0.133] | 1.723 | 0.103 | 0.1248 |

Diferencias pareadas (modelo − baseline; IC 95 % < 0 en Brier y log loss = supera):
- vs Modelo 1.0.0 (spec 005): **supera** (Δ Brier -0.0030 [-0.005, -0.002])
- vs Regresión logística: **supera** (Δ Brier -0.0089 [-0.012, -0.006])
- vs Pronóstico crudo: **supera** (Δ Brier -0.0334 [-0.038, -0.029])
- vs Climatología: **supera** (Δ Brier -0.0158 [-0.021, -0.011])

| Nivel de alerta | % de horas | Llueve dentro del nivel |
|---|---|---|
| VERDE | 86.6 % | 14.3 % |
| AMARILLO | 10.4 % | 63.9 % |
| ROJO | 3.0 % | 82.0 % |

Alerta ≥ AMARILLO: precisión 0.680, sensibilidad 0.424 · ROJO: precisión 0.820, sensibilidad 0.115.

## Qué features importan y por qué (desarrollo, *out-of-fold*)

### Candidatas evaluadas (configuración de referencia 1.0.0)

| Conjunto | Log loss CV | Δ vs base (± EE) | Log loss CV espacial (celda fuera) |
|---|---|---|---|
| `base` | 0.3088 | 0.0000 ± 0.0000 | 0.3319 |
| `base+window` | 0.3026 | -0.0062 ± 0.0015 | 0.3209 |
| `base+location` | 0.3006 | -0.0082 ± 0.0013 | 0.3227 |
| `base+window+location` | 0.2964 | -0.0123 ± 0.0014 | 0.3110 |

| Aporte marginal | Δ log loss (± EE) | > 1 EE |
|---|---|---|
| window dado base | -0.0062 ± 0.0015 | sí |
| window dado location | -0.0041 ± 0.0013 | sí |
| location dado base | -0.0082 ± 0.0013 | sí |
| location dado window | -0.0062 ± 0.0007 | sí |

### Ablación del modelo elegido (Δ log loss al quitar el grupo; positivo = el grupo ayuda)

| Grupo | Features | Δ log loss (± EE) |
|---|---|---|
| hora del día | `hour_sin`, `hour_cos` | 0.0143 ± 0.0014 |
| ubicación | `latitude`, `longitude` | 0.0075 ± 0.0010 |
| ventana del pronóstico | `precipitation_prev2_log1p`, `precipitation_prev1_log1p`, `precipitation_next1_log1p`, `precipitation_next2_log1p`, `cloud_cover_prev1`, `cloud_cover_next1`, `cape_prev1_log1p`, `cape_next1_log1p`, `precipitation_5h_log1p` | 0.0062 ± 0.0011 |
| termodinámica | `temperature_2m`, `relative_humidity_2m`, `dew_point_depression` | 0.0047 ± 0.0024 |
| viento | `wind_u`, `wind_v` | 0.0044 ± 0.0010 |
| estacionalidad | `month_sin`, `month_cos` | 0.0023 ± 0.0030 |
| precipitación pronosticada | `precipitation_log1p` | 0.0016 ± 0.0009 |
| nubosidad | `cloud_cover` | 0.0013 ± 0.0002 |
| inestabilidad (CAPE) | `cape_log1p` | 0.0010 ± 0.0004 |
| presión | `pressure_msl` | 0.0006 ± 0.0004 |

### Importancia por permutación (aumento del log loss, IC 95 % entre folds × repeticiones)

| # | Feature | Importancia |
|---|---|---|
| 1 | `hour_cos` | 0.0699 [0.031, 0.109] |
| 2 | `hour_sin` | 0.0508 [0.031, 0.068] |
| 3 | `precipitation_5h_log1p` | 0.0185 [0.011, 0.033] |
| 4 | `dew_point_depression` | 0.0073 [0.001, 0.016] |
| 5 | `wind_u` | 0.0070 [0.002, 0.015] |
| 6 | `longitude` | 0.0065 [0.004, 0.009] |
| 7 | `cape_prev1_log1p` | 0.0061 [0.002, 0.012] |
| 8 | `latitude` | 0.0047 [0.003, 0.010] |
| 9 | `precipitation_prev2_log1p` | 0.0027 [-0.001, 0.005] |
| 10 | `temperature_2m` | 0.0021 [-0.002, 0.008] |

### Dependencia parcial de las principales, contrastada con la física

| Feature | Tendencia de la PDP | Esperado |
|---|---|---|
| `precipitation_5h_log1p` | creciente | creciente (más lluvia pronosticada, más probabilidad) — ✔ concuerda |
| `dew_point_depression` | decreciente | decreciente (a menor depresión, más saturación) — ✔ concuerda |
| `wind_u` | creciente | sin expectativa física fuerte |
| `longitude` | no monotónica | sin expectativa física fuerte |

**Ciclo diurno** (dependencia parcial conjunta de `hour_sin` y `hour_cos`): El modelo aprendió un ciclo diurno con máximo a las 14:00 (P media 46.4 %) y mínimo a las 1:00 (8.6 %); en el último fold la lluvia observada fue máxima a las 14:00 (55.8 %). Las tormentas de la tarde en el valle son el patrón esperado.

Figuras: `reports/figures/study_permutation_importance.png`, `study_partial_dependence.png`, `study_hour_profile.png`, `study_ablation.png`.

**Curva de aprendizaje** (log loss medio en los 3 folds recientes según los meses de entrenamiento): 3 meses: 0.5110 · 6 meses: 0.4214 · 12 meses: 0.3467 · 18 meses: 0.3413 · todo meses: 0.3373.
Figura: `reports/figures/study_learning_curve.png`.

## Dónde falla (predicciones *out-of-fold* de desarrollo)

| Temporada | Horas | Llueve | Predicho medio | ROC-AUC | ECE |
|---|---|---|---|---|---|
| lluviosa | 75,816 | 20.4 % | 23.6 % | 0.849 | 0.032 |
| seca | 86,112 | 11.3 % | 12.4 % | 0.888 | 0.012 |
| transición | 9,672 | 6.4 % | 13.2 % | 0.898 | 0.069 |

- Horas locales con peor Brier: 17 (Brier 0.186, AUC 0.75), 16 (Brier 0.186, AUC 0.78), 15 (Brier 0.178, AUC 0.80).
- Celdas ERA5 con peor Brier: 6.25,-75.75 (Brier 0.097, AUC 0.87), 6.0,-75.75 (Brier 0.096, AUC 0.84), 6.25,-75.5 (Brier 0.092, AUC 0.87).
- Por lluvia pronosticada (mm/h): >2 (Brier 0.206, AUC 0.73), (0.5, 2] (Brier 0.204, AUC 0.74), (0.1, 0.5] (Brier 0.159, AUC 0.81).

## Calibración y umbrales

Calibración elegida por *cross-fitting* temporal (cada fold se calibra solo con los anteriores):

| Método | Log loss | ECE |
|---|---|---|
| `none` | 0.3021 | 0.0273 |
| `isotonic` | 0.3030 | 0.0052 |
| `sigmoid` | 0.3014 | 0.0036 |

Curvas de costo (costo de una falsa alarma = 1, de una lluvia no avisada = r). Con probabilidades calibradas el umbral
óptimo teórico es 1/(1+r); el óptimo empírico coincide, lo que confirma la calibración. *Regret* = costo extra por hora
de usar el corte de negocio en lugar del óptimo:

| Razón de costo | Umbral teórico | Umbral óptimo | *Regret* AMARILLO (0.40) | *Regret* ROJO (0.70) |
|---|---|---|---|---|
| 1 : 1 | 0.50 | 0.48 | 0.0033 | 0.0135 |
| 1 : 2 | 0.33 | 0.33 | 0.0032 | 0.0730 |
| 1 : 3 | 0.25 | 0.27 | 0.0243 | 0.1538 |
| 1 : 4 | 0.20 | 0.23 | 0.0564 | 0.2455 |
| 1 : 5 | 0.17 | 0.17 | 0.0976 | 0.3463 |

Lectura: 0.40 es casi óptimo cuando no avisar una lluvia cuesta 1–2 veces una falsa alarma (alerta de "lleve paraguas");
0.70 corresponde a una alerta fuerte en la que las falsas alarmas se penalizan más. Se conservan (charter RF-10).
Figuras: `reports/figures/study_calibration.png`, `study_decision_cost.png`, `rain_classifier_reliability.png`.

## Validación externa contra pluviómetros SIATA (jun–jul 2022, fuera del entrenamiento)

7,834 horas-estación; llueve en el pluviómetro en el 19.4 %.

| Puntaje | ROC-AUC frente a la lluvia medida |
|---|---|
| Modelo | 0.511 |
| Precipitación pronosticada (cruda) | 0.536 |
| Precipitación de referencia ERA5 (la etiqueta) | 0.532 |

## Registro de decisiones (qué periodo tocó cada una)

| Decisión | Datos usados | Evidencia |
|---|---|---|
| ventana del pronóstico adoptada | CV temporal desarrollo 2022–2024 | `study.json:feature_candidates.marginal` |
| ubicación (lat/lon) adoptada | CV temporal y espacial (dejar una celda ERA5 fuera), desarrollo | `study.json:feature_candidates.marginal, spatial_cv` |
| hgb {'learning_rate': 0.097271, 'max_leaf_nodes': 29, 'min_samples_leaf': 200, 'l2_regularization': 0.04605, 'max_features': 0.520807, 'max_iter': 159} (regla de 1 EE) | CV desarrollo 2022–2024 | `study.json:search` |
| calibración = sigmoid | cross-fitting temporal sobre OOF de desarrollo | `study.json:calibration` |
| umbrales 0.40/0.70 (RF-10) contrastados con el umbral de costo mínimo | OOF calibrado de desarrollo (folds 2–6) | `study.json:decision` |
| modelo final hgb entrenado en todo desarrollo con calibración sigmoid (mapa OOF) | desarrollo 2022–2024 | `metadata.json` |
| evaluación única en 2025 y en el holdout fresco 2026 (ninguna decisión usa estos periodos) | 2025 (ya visto por 1.0.0) y 2026-01 → 2026-10-15 | `metrics.json:splits` |

## Limitaciones

- La etiqueta es reanálisis (ERA5, ~25 km), no lluvia medida: el modelo predice lluvia **de la celda**. Frente a
  pluviómetros, la concordancia horaria es baja con cualquier fuente de malla (`reports/metrics/label_validation.json`).
- Las 13 estaciones caen en 5 celdas y sus etiquetas están muy correlacionadas: hay muchas menos observaciones
  independientes que filas. Por eso los IC se calculan remuestreando días completos.
- La ubicación generaliza a celdas no vistas dentro del valle (validación espacial), pero no se evaluó fuera de él;
  el contrato rechaza coordenadas fuera del Valle de Aburrá.
- La tasa de lluvia varía entre años; la calibración se ajustó con predicciones *out-of-fold* de 2023–2024.
- 2025 ya se había usado para reportar la versión 1.0.0; por eso el holdout 2026 es la estimación más limpia.
