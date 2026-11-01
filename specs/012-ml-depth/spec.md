# Feature Specification: Profundidad de ML — búsqueda, interpretabilidad, ablación, errores, calibración y holdout fresco

**Feature Branch**: `012-ml-depth` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Implemented (2026-10-31)

**Input**: User description: "Spec 012 (charter R-45–R-51): el ML es el centro del portafolio. Búsqueda de hiperparámetros defendible con validación cruzada temporal rolling-origin y análisis de sensibilidad; interpretabilidad (permutación con IC, dependencia parcial/ICE) contrastada con la física; ablación por grupos de features y curva de aprendizaje; análisis de errores por hora, temporada, ubicación y nivel de lluvia pronosticada; calibración re-evaluada (meta ECE < 0.03) y umbrales justificados con análisis de decisión; evaluación final única en un holdout fresco (2026); notebook 3.0 que narra el proceso desde artefactos generados."

## Clarifications

### Session 2026-10-31

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Qué periodos usa cada decisión? → A: **Desarrollo** = 2022–2024 (sin jun–jul 2022, reservados a la validación externa SIATA). Toda decisión (hiperparámetros, features, calibración, umbrales) se toma con validación cruzada temporal dentro de desarrollo. **2025** queda como prueba "ya vista" (se usó para reportar la versión 1.0.0) y **2026-01-01 → último día con etiqueta** como holdout fresco, evaluado **una sola vez** con el modelo final. Un registro (`decision_log`) dice qué periodo tocó cada decisión.
- Q: ¿Cómo son los folds? → A: *Rolling origin* con ventana de entrenamiento creciente: 6 folds trimestrales de validación entre 2023-07 y 2024-12, cada uno entrenado con todo lo anterior, con un hueco de 24 h entre entrenamiento y validación (autocorrelación horaria).
- Q: ¿Qué búsqueda de hiperparámetros? → A: Búsqueda aleatoria con semilla fija, 60 configuraciones de `HistGradientBoostingClassifier` (tasa de aprendizaje log-uniforme, hojas, mínimo de muestras por hoja, regularización L2, fracción de features, iteraciones), más familias de referencia con su propia búsqueda pequeña: regresión logística con *splines* (un GAM simple) y `RandomForestClassifier` (la familia del modelo heredado). Objetivo: log loss medio entre folds (propiedad para probabilidades); se reporta media ± desvío y la regla de "un error estándar" para preferir el modelo más simple.
- Q: ¿Se agregan features nuevas? → A: Solo si la ablación lo justifica y están disponibles en inferencia con la misma fuente. Candidatos evaluados: (a) **ventana del pronóstico** (precipitación, nubosidad y CAPE de las horas t−2…t+2 del mismo pronóstico, disponibles en producción porque Open-Meteo entrega la serie horaria completa) y (b) **ubicación** (lat/lon). La ubicación se evalúa además con validación espacial (dejar una celda ERA5 fuera): si no generaliza a celdas no vistas, se descarta, porque el heatmap y las rutas predicen en puntos arbitrarios.
- Q: Si cambian las features, ¿qué pasa con el contrato y los servicios? → A: Cambio de contrato de features versionado (1.0.0 → 1.1.0, aditivo en entradas: la ventana se envía como campos opcionales `*_prev2…*_next2`), con el ML API, el Backend y el routing service actualizados para enviarlos desde la misma respuesta de Open-Meteo. Sin la ventana, el ML API rechaza la petición con 422 (no se rellenan valores: constitución VI).
- Q: ¿Cómo se eligen los umbrales? → A: Se conservan 0.40/0.70 (RF-10) salvo evidencia en contra; se justifican con curvas de costo esperado para razones de costo falsa alarma : lluvia no avisada entre 1:1 y 1:5, y con precisión/sensibilidad por nivel, sobre predicciones *out-of-fold* de desarrollo.
- Q: ¿Interpretabilidad con SHAP? → A: No: scikit-learn ya da importancia por permutación y dependencia parcial/ICE; agregar SHAP sería una dependencia sin necesidad (constitución).

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien evalúa** al autor para un rol de ciencia de datos (lee el README, la model card, el notebook y los JSON) y **la persona que usa la app** (probabilidades mejor calibradas y alertas más útiles).

### User Story 1 - Cada decisión de modelado tiene evidencia reproducible (Priority: P1)

Quien evalúa puede ver, para el modelo final, el espacio de búsqueda, todos los ensayos con su desempeño por fold, por qué se eligió la configuración y cuánto cambia el resultado al mover cada hiperparámetro.

**Why this priority**: es la demostración central de criterio en modelado; hoy la selección es una grilla de 16 combinaciones evaluada en un único año.

**Independent Test**: `make study` regenera `reports/metrics/rain_classifier/study/*.json` y las figuras; con la misma semilla y datos, los resultados coinciden.

**Acceptance Scenarios**:

1. **Given** el dataset, **When** se ejecuta el estudio, **Then** existe una tabla con ≥ 60 ensayos de HGB y las familias de referencia, con log loss por fold, media y desvío, y la configuración elegida por la regla de un error estándar.
2. **Given** los ensayos, **When** se grafican, **Then** hay una figura de sensibilidad por hiperparámetro.
3. **Given** la misma semilla y huella de datos, **When** se repite, **Then** la configuración elegida y las métricas coinciden (|Δ log loss| < 1e-4).

---

### User Story 2 - El modelo se explica y concuerda con la física (Priority: P1)

Quien evalúa ve qué variables importan, con incertidumbre, y cómo cambia la probabilidad con cada una, contrastado con lo esperado meteorológicamente (más lluvia pronosticada, más humedad, más CAPE y la tarde → más probabilidad).

**Independent Test**: el estudio produce importancias por permutación con IC y curvas PDP/ICE de las 4 features principales; la model card las comenta.

**Acceptance Scenarios**:

1. **Given** el modelo de desarrollo, **When** se calcula la importancia por permutación sobre los folds de validación, **Then** cada feature tiene media e IC 95 % de la caída de log loss.
2. **Given** las 4 features más importantes, **When** se calcula la dependencia parcial, **Then** las curvas se guardan como figura y JSON, y la model card indica si el signo concuerda con la física.

---

### User Story 3 - Las features y el volumen de datos están justificados (Priority: P1)

Quien evalúa ve cuánto aporta cada grupo de features (reentrenando sin él), si las features candidatas mejoran, si la ubicación generaliza a celdas no vistas, y si más datos ayudarían.

**Independent Test**: tablas de ablación (CV temporal y espacial) y curva de aprendizaje.

**Acceptance Scenarios**:

1. **Given** los grupos de features, **When** se quita cada uno, **Then** se reporta Δ log loss medio ± desvío entre folds.
2. **Given** las features candidatas, **When** se agregan, **Then** se adoptan solo si mejoran el log loss medio en más de un error estándar en la CV temporal (y, para la ubicación, también en la espacial).
3. **Given** fracciones crecientes del entrenamiento (los últimos 3, 6, 12, 18 meses antes de cada fold), **When** se entrenan, **Then** se reporta la curva de aprendizaje.

---

### User Story 4 - Se sabe dónde y cuándo falla el modelo (Priority: P2)

**Independent Test**: métricas *out-of-fold* por segmento.

**Acceptance Scenarios**:

1. **Given** las predicciones *out-of-fold*, **When** se segmentan por hora local, temporada (secas/lluviosas), celda ERA5 y bin de lluvia pronosticada, **Then** se reportan ROC-AUC, Brier, tasa observada y ECE por segmento, y la model card resume los 3 segmentos peores.

---

### User Story 5 - Probabilidades calibradas y umbrales con criterio de decisión (Priority: P1)

La persona recibe alertas cuyos porcentajes significan lo que dicen, y quien evalúa ve por qué los cortes 0.40/0.70 son razonables.

**Independent Test**: comparación de calibraciones con *cross-fitting* temporal; curvas de costo.

**Acceptance Scenarios**:

1. **Given** las predicciones *out-of-fold*, **When** se comparan sin calibrar, isotónica y sigmoide (ajustadas siempre en datos anteriores al fold evaluado), **Then** se elige por log loss y se reporta ECE; el modelo final cumple ECE < 0.03 en desarrollo o la model card explica por qué no.
2. **Given** razones de costo 1:1 a 1:5, **When** se calcula el umbral óptimo, **Then** se reporta junto a los cortes 0.40/0.70 con su costo relativo.

---

### User Story 6 - Evaluación final honesta en datos nunca vistos (Priority: P1)

**Independent Test**: `make train` produce el modelo 1.1.0 y lo evalúa una vez en 2025 y en el holdout fresco 2026, frente a los baselines y a la versión 1.0.0.

**Acceptance Scenarios**:

1. **Given** el modelo final, **When** se evalúa en 2026, **Then** `metrics.json` trae las métricas con IC por bootstrap en bloques de días, la comparación pareada con climatología, pronóstico crudo, regresión logística y el modelo 1.0.0, y el `decision_log` muestra que 2026 no tocó ninguna decisión.
2. **Given** el modelo final, **When** se sirve, **Then** el ML API carga la versión 1.1.0 y los servicios envían las entradas del contrato vigente.

---

### User Story 7 - Un notebook narra el proceso (Priority: P2)

**Acceptance Scenarios**:

1. **Given** los artefactos generados, **When** se ejecuta `notebooks/3.0-nm-evaluacion-y-calibracion.ipynb`, **Then** muestra el estudio leyendo solo `reports/` (sin entrenar ni recalcular métricas) y se guarda con salidas ligeras.

### Edge Cases

- El holdout 2026 aún no tiene etiqueta para las últimas horas (ERA5 llega con días de retraso): se corta en el último día completo con etiqueta y se registra la fecha.
- Un fold sin positivos en algún segmento: el segmento se reporta con `n` y sin métricas indefinidas.
- Si el modelo final **no** supera a algún baseline en 2026, se publica igual y se documenta (P4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Un único módulo de estudio MUST ejecutar todos los experimentos con semilla fija y escribir JSON y figuras generados (nunca editados a mano).
- **FR-002**: La CV MUST ser temporal *rolling origin* (6 folds, hueco 24 h) dentro de desarrollo; MUST NOT usar 2025 ni 2026.
- **FR-003**: La búsqueda MUST incluir ≥ 60 configuraciones de HGB y familias de referencia (logística con *splines*, bosque aleatorio), con tabla completa persistida y regla de un error estándar.
- **FR-004**: La importancia por permutación MUST reportar IC 95 %; la dependencia parcial MUST cubrir las 4 features principales.
- **FR-005**: La ablación MUST cubrir cada grupo de features y las candidatas; la ubicación MUST evaluarse también con validación espacial por celda.
- **FR-006**: El análisis de errores MUST segmentar por hora local, temporada, celda y bin de lluvia pronosticada.
- **FR-007**: La calibración MUST elegirse con *cross-fitting* temporal; los umbrales MUST justificarse con curvas de costo.
- **FR-008**: El modelo final MUST evaluarse una sola vez en 2025 y en 2026, contra baselines y la versión 1.0.0, con IC por bootstrap en bloques de días.
- **FR-009**: Un `decision_log` MUST listar cada decisión, la evidencia y el periodo usado.
- **FR-010**: Si cambian las features, el contrato MUST versionarse y todos los servicios MUST enviar las entradas nuevas desde la misma fuente; un test de paridad MUST demostrarlo.
- **FR-011**: El notebook 3.0 MUST leer solo artefactos de `reports/`.
- **FR-012**: La model card MUST generarse con las secciones de búsqueda, interpretabilidad, ablación, errores, calibración/umbrales y holdout fresco.

### Key Entities

- **Ensayo**: familia, hiperparámetros, log loss por fold, media, desvío, tiempo.
- **Decisión**: qué se decidió, evidencia (archivo/campo), periodo de datos usado.
- **Segmento**: dimensión, valor, n, tasa observada, métricas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `make study` y `make train` se reproducen desde un clon con datos (semillas fijas; determinismo verificado de punta a punta con datos sintéticos).
- **SC-002**: El modelo final mejora el log loss *out-of-fold* de desarrollo frente a la configuración 1.0.0 en más de un error estándar, o se documenta que no.
- **SC-003**: ECE < 0.03 en desarrollo (*out-of-fold*) y se reporta en 2025 y 2026.
- **SC-004**: El holdout 2026 se evalúa una sola vez y el `decision_log` lo prueba.
- **SC-005**: El estudio completo corre en < 60 min en un portátil de 12 núcleos.

## Assumptions

- Open-Meteo (Historical Forecast y ERA5) entrega 2026 hasta unos días antes de hoy.
- La etiqueta sigue siendo la de la spec 003 (ERA5 ≥ 0.5 mm/h); su limitación frente a pluviómetros se mantiene documentada.
