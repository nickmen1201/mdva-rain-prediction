# Research: Profundidad de ML

Las cifras de este documento salen de `reports/metrics/rain_classifier/study/study.json` y de `reports/metrics/rain_classifier/1.1.0/metrics.json`; aquí se explican las decisiones, no se reportan resultados (R-44).

## R1. Punto de partida (modelo 1.0.0, spec 005)

| ID | Hallazgo | Consecuencia |
|---|---|---|
| H-39 | La selección era una grilla de 16 HGB evaluada en **un** año (2024) | Elección sensible a un solo régimen de lluvia (2024 fue el año más seco de los cuatro) |
| H-40 | La calibración se decidió con un sub-split de 6 meses de 2024 y quedó en "ninguna"; el ECE en 2025 fue 0.035 (meta < 0.03) | Probabilidades algo sobreconfiadas usadas contra umbrales de negocio |
| H-41 | La persistencia (no desplegable) casi empataba al modelo en ROC-AUC | El modelo extraía poca información más allá de "llueve si el pronóstico dice que llueve ahora" |
| H-42 | 2025 ya se había usado para comparar estrategias de calibración (transparencia de la model card 1.0.0) | Hacía falta un periodo nunca visto: 2026 |

## R2. Validación cruzada

- **Decision**: *rolling origin* con 6 folds trimestrales (2023-T3 … 2024-T4), ventana de entrenamiento creciente y hueco de 24 h.
- **Rationale**: respeta el orden temporal (el modelo siempre predice el futuro), el hueco evita que la autocorrelación horaria filtre información y los trimestres cubren las dos temporadas lluviosas y secas del valle. 2025 y 2026 quedan fuera de toda decisión.
- **Alternatives considered**: `TimeSeriesSplit` con folds de igual tamaño (no alinea con trimestres ni temporadas); K-fold aleatorio (optimista por autocorrelación); *blocked* CV con datos futuros en el entrenamiento (viola la causalidad del uso real).

## R3. Regla de un error estándar: debe ser **pareada** (hallazgo durante el estudio)

- **Problema encontrado (H-38)**: la primera corrida usó el EE de la **media** del log loss entre folds. Como los trimestres tienen tasas de lluvia muy distintas, el log loss por fold varía mucho (≈ 0.25–0.38) y ese EE resultó ≈ 0.04: casi todas las configuraciones quedaban "dentro de 1 EE" y la regla eligió una muy simple que era peor **en todos los folds**.
- **Decision**: EE de la **diferencia por fold** frente a la mejor configuración (los folds son los mismos para todos los ensayos, así que la comparación pareada elimina la variación entre trimestres). Elegible: diferencia media ≤ su EE pareado; entre los elegibles, la menor complejidad (`max_iter × max_leaf_nodes`). Test: `test_un_error_estandar_es_pareado_entre_folds_heterogeneos`.
- **Por qué importa**: es el mismo error que comparar dos modelos con IC no pareados en un bootstrap; la versión pareada es la que responde la pregunta "¿es este modelo peor que el mejor?".

## R4. Espacio de búsqueda

- **Decision**: 60 configuraciones aleatorias (semilla 42) de `HistGradientBoostingClassifier`: `learning_rate` log-uniforme [0.02, 0.3], `max_leaf_nodes` log-uniforme entero [7, 63], `min_samples_leaf` ∈ {20, 50, 100, 200, 400}, `l2_regularization` log-uniforme [1e-3, 10], `max_features` uniforme [0.5, 1], `max_iter` entero [100, 800], sin *early stopping* (determinismo y comparabilidad entre folds).
- **Familias de referencia**: logística sobre *splines* cúbicos (6 nudos por feature, C ∈ {0.1, 1}): un GAM aditivo que responde "¿hacen falta interacciones?"; bosque aleatorio (150 árboles, `max_samples=0.3`): la familia del modelo heredado.
- **Alternatives considered**: Optuna/TPE (dependencia nueva; con ~40 s por ensayo, 60 ensayos aleatorios cubren bien 6 dimensiones); *successive halving* (submuestrear filas rompe la estructura temporal de los folds).

## R5. Features candidatas

- **Ventana del pronóstico** (t−2…t+2 de precipitación; t±1 de nubosidad y CAPE; suma de 5 h): el pronóstico numérico suele acertar el evento pero no la hora exacta; los vecinos del **mismo** pronóstico absorben ese desfase. Están disponibles en producción (Open-Meteo entrega la serie horaria), así que no hay *skew* ni fuga: son pronósticos, no observaciones.
- **Ubicación** (lat/lon): en 1.0.0 se descartó por miedo a memorizar 5 celdas. Se evalúa con **validación espacial** (entrenar sin una celda ERA5, evaluar en ella): si no generaliza a celdas no vistas, se descarta, porque el producto predice en puntos arbitrarios del valle.
- **Regla**: se adopta un grupo si su aporte marginal (con y sin el otro grupo) mejora el log loss en más de 1 EE pareado y, para la ubicación, si además mejora la CV espacial.

## R6. Calibración

- **Decision**: *cross-fitting* temporal: el fold k se calibra con las predicciones *out-of-fold* de los folds 1…k−1; se comparan identidad, isotónica y Platt (sigmoide sobre el logit) por log loss. El modelo final aplica el mapa ajustado sobre todas las OOF de desarrollo (`mdva/modeling/calibration.py`, serializable con el modelo).
- **Rationale**: calibrar sobre los mismos datos de entrenamiento subestima la sobreconfianza; calibrar sobre un único bloque posterior desperdicia datos. La comparación *cross-fitted* es honesta y usa todo desarrollo.

## R7. Umbrales

- **Decision**: curvas de costo esperado por hora con costo(falsa alarma) = 1 y costo(lluvia no avisada) = r ∈ {1, …, 5} sobre OOF calibradas. Con probabilidades calibradas el umbral óptimo es 1/(1+r); que el empírico coincida es una prueba adicional de calibración. Se reporta el *regret* de los cortes de negocio 0.40/0.70, que se conservan (RF-10).

## R8. Interpretabilidad

- **Decision**: importancia por permutación sobre los folds de validación (5 repeticiones × 6 folds, IC 95 % por percentiles), PDP/ICE de las 4 features continuas más importantes y **dependencia parcial conjunta de la hora** (fijar `hour_sin` y `hour_cos` a la vez para cada hora local), contrastada con la tasa observada por hora.
- **Rationale**: la PDP de `hour_sin` o `hour_cos` por separado no tiene interpretación (la hora es un punto en el círculo); el perfil conjunto sí. SHAP no se agrega: scikit-learn basta y la constitución pide justificar dependencias.

## R9. Holdout fresco

- **Decision**: 2026-01-01 → 2026-10-15 (fecha fija: ERA5 llega con días de retraso), en `data/processed/rain_hourly_holdout_2026.parquet` con su propia huella y su reporte de calidad (`reports/data_quality_holdout.json`), construido por el mismo pipeline y contratos (periodo ajustado). Se evalúa una sola vez en `make train`; el `decision_log` muestra que ninguna decisión lo usó.
