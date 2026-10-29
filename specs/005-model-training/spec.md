# Feature Specification: Entrenamiento con validación temporal, baselines y calibración

**Feature Branch**: `005-model-training` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Implemented (2026-10-29)

**Input**: User description: "Reemplazar el entrenamiento actual (sin holdout, sin baselines, probabilidades no calibradas, métricas a mano) por uno reproducible con split temporal, baselines, calibración, intervalos de confianza, seguimiento de corridas y model card (charter R-11–R-18; H-07, H-08, H-13, H-14; constitución VI)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates"), apoyadas en el experimento exploratorio del research.

- Q: ¿Cómo se divide el tiempo? → A: Entrenamiento 2022–2023, validación 2024 (selección de modelo y calibración), prueba 2025 (se usa una sola vez, para el reporte final). Se dejan 24 h de separación al inicio de validación y de prueba. Junio y julio de 2022 se excluyen del entrenamiento para usarlos como validación externa contra los pluviómetros SIATA (spec 003).
- Q: ¿Con qué métrica se elige el modelo? → A: Log loss en validación (regla de puntuación propia; premia probabilidades bien calibradas, que es lo que consumen los umbrales de negocio). ROC-AUC, PR-AUC y Brier se reportan como complemento.
- Q: ¿Qué baselines? → A: Climatología (tasa de lluvia por hora local × mes, estimada en entrenamiento), pronóstico crudo (solo la precipitación pronosticada) y regresión logística con todas las features. Persistencia (la etiqueta de la hora anterior) se reporta como **referencia no desplegable**: esa información no existe en producción.
- Q: ¿Se cambian los umbrales de negocio 0.40 / 0.70 (charter RF-10)? → A: No. Se aplican sobre probabilidades calibradas y se reporta qué significan (precisión, sensibilidad, frecuencia de cada nivel de alerta) en prueba.
- Q: ¿Dónde se guarda el modelo? → A: En git, si pesa menos de 5 MB (charter P7); si no, como asset de un release con checksum.
- Q: ¿"Sin calibración posterior" es una opción válida del método de calibración (FR-005)? → A: Sí, si se elige en validación con el mismo criterio que las demás. Agregado tras la primera corrida real (research R10).

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien revisa** el portafolio (evaluador de Ciencia de Datos) y **quien desarrolla** (reentrena y despliega).

### User Story 1 - Entrenar un modelo reproducible con un comando (Priority: P1)

Con el dataset de la spec 003 construido, un comando entrena los candidatos, elige el mejor en validación, lo calibra, lo guarda junto con sus metadatos y registra la corrida. Repetir el comando produce el mismo modelo y las mismas métricas.

**Why this priority**: hoy no hay forma de reproducir el modelo en producción (datos perdidos, sin seeds registradas ni metadatos).

**Independent Test**: ejecutar el comando dos veces y comparar métricas y huella del modelo.

**Acceptance Scenarios**:

1. **Given** el dataset construido, **When** se ejecuta el comando de entrenamiento, **Then** queda un modelo con metadatos (versión, huella de los datos, periodo de cada split, features y su versión de contrato, versiones de librerías, semilla, umbrales, métricas) y un registro de la corrida.
2. **Given** dos ejecuciones con los mismos datos y código, **When** se comparan, **Then** las métricas son idénticas.
3. **Given** un entorno con una versión de la librería de ML distinta a la registrada, **When** se intenta cargar el modelo, **Then** la carga falla con un mensaje explícito.

---

### User Story 2 - Evaluación honesta frente a baselines (Priority: P1)

Un revisor ve, para el año de prueba no usado en ninguna decisión, el desempeño del modelo y de cada baseline con intervalos de confianza, y sabe si el modelo aporta algo frente a lo que ya da el pronóstico numérico.

**Why this priority**: constitución VI; las cifras publicadas del modelo anterior no se pueden reproducir y se contradicen entre sí (H-07).

**Independent Test**: abrir el reporte de métricas y comprobar que contiene cada métrica para cada modelo y baseline, con intervalo, en el año de prueba.

**Acceptance Scenarios**:

1. **Given** el modelo entrenado, **When** se evalúa, **Then** el reporte contiene ROC-AUC, PR-AUC, Brier, log loss y Brier skill score frente a la climatología, para el modelo y cada baseline, con intervalos de confianza por bootstrap en bloques de días.
2. **Given** el reporte, **When** el modelo no supera a un baseline desplegable en alguna métrica, **Then** el reporte lo dice explícitamente.

---

### User Story 3 - Las probabilidades significan lo que dicen (Priority: P2)

Cuando el sistema dice "70 % de probabilidad de lluvia", llueve aproximadamente 7 de cada 10 veces; y los niveles VERDE / AMARILLO / ROJO tienen un significado medible.

**Why this priority**: los umbrales de negocio se aplicaban a probabilidades sesgadas por el balanceo de clases (H-08).

**Independent Test**: revisar el diagrama de confiabilidad y la tabla de niveles en el año de prueba.

**Acceptance Scenarios**:

1. **Given** el modelo calibrado, **When** se agrupan las predicciones de prueba por probabilidad, **Then** la frecuencia observada en cada grupo queda cerca de la probabilidad media del grupo (error de calibración esperado reportado).
2. **Given** los umbrales 0.40 y 0.70, **When** se evalúan en prueba, **Then** el reporte da, por nivel, la frecuencia del nivel y la tasa de lluvia observada dentro de él, y la precisión y sensibilidad de "alerta ≥ AMARILLO" y "alerta ROJO".

---

### User Story 4 - Validación externa contra pluviómetros (Priority: P2)

Un revisor ve cómo se compara el modelo con los pluviómetros SIATA en el mes que no se usó para entrenar, frente al pronóstico crudo y a la etiqueta misma.

**Why this priority**: la etiqueta es reanálisis; esta es la única evidencia frente a lluvia medida en un punto.

**Independent Test**: revisar la sección de validación externa del reporte.

**Acceptance Scenarios**:

1. **Given** el modelo y los pluviómetros SIATA de junio–julio de 2022, **When** se evalúa, **Then** el reporte da ROC-AUC y kappa (al umbral AMARILLO) del modelo frente a la lluvia medida, junto a los de la etiqueta y el pronóstico crudo.

---

### User Story 5 - Model card (Priority: P3)

Un revisor encuentra en un documento corto qué predice el modelo, con qué datos se entrenó, cómo se evaluó, cuáles son sus números y sus limitaciones conocidas, todo citando el reporte generado.

**Why this priority**: comunicación; cierra el ciclo de "resultados que no se escriben a mano" (charter R-44).

**Independent Test**: comprobar que las cifras de la model card coinciden con el reporte (prueba automática).

**Acceptance Scenarios**:

1. **Given** la model card, **When** se comparan sus cifras con el reporte de métricas, **Then** coinciden.

### Edge Cases

- La tasa de lluvia cambia entre años (19 %, 16 % y 22 % en 2022–23, 2024 y 2025): la calibración ajustada en 2024 puede quedar corrida en 2025; el reporte mide la calibración en prueba, no en validación.
- Estaciones que comparten celda tienen la misma etiqueta: el número efectivo de observaciones independientes es menor que el número de filas; el bootstrap remuestrea días completos (todas las estaciones juntas) para no subestimar la incertidumbre.
- Probabilidades exactamente 0 o 1 tras la calibración isotónica: se recortan antes de calcular log loss.
- El modelo anterior (`models/random_forest.pkl`) sigue sirviendo hasta la spec 006; esta spec no lo borra.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Un comando MUST entrenar, seleccionar, calibrar, evaluar y guardar el modelo a partir del dataset de la spec 003, usando el módulo único de features (spec 004).
- **FR-002**: El split MUST ser temporal (Clarifications) con 24 h de separación y sin que ningún dato de prueba influya en ninguna decisión (selección, calibración, umbrales).
- **FR-003**: El reporte MUST incluir los baselines climatología, pronóstico crudo y regresión logística, y persistencia como referencia no desplegable.
- **FR-004**: El reporte MUST incluir ROC-AUC, PR-AUC, Brier, log loss, Brier skill score, error de calibración esperado y curva de confiabilidad, con intervalos del 95 % por bootstrap en bloques de días.
- **FR-005**: Las probabilidades servidas MUST estar calibradas, con el método de calibración (incluida la opción de no recalibrar) elegido en validación.
- **FR-006**: El reporte MUST describir los niveles de alerta 0.40 / 0.70 en prueba (US3).
- **FR-007**: El reporte MUST incluir la validación externa contra pluviómetros SIATA (US4).
- **FR-008**: Cada modelo guardado MUST llevar metadatos completos (US1) y una model card cuyas cifras salen del reporte.
- **FR-009**: Cargar un modelo con una versión de la librería de ML o del contrato de features distinta a la registrada MUST fallar con un mensaje explícito.
- **FR-010**: Cada corrida de entrenamiento MUST quedar registrada (parámetros, huella de datos, versión de código, métricas).
- **FR-011**: El entrenamiento MUST ser determinista (semilla fija y registrada).
- **FR-012**: El modelo guardado MUST pesar menos de 5 MB para versionarse en git; si no, se publica como asset con checksum.

### Key Entities

- **Modelo**: clasificador calibrado + metadatos + model card, versionado.
- **Reporte de métricas**: resultados por modelo/baseline y split, con intervalos.
- **Registro de corrida**: parámetros, huellas y métricas de una ejecución.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dos ejecuciones del entrenamiento con los mismos datos producen métricas idénticas.
- **SC-002**: En el año de prueba, el modelo supera a la climatología y al pronóstico crudo en log loss y en Brier, con intervalos del 95 % de la diferencia que excluyen el 0; si no ocurre, el reporte lo declara y la model card lo explica.
- **SC-003**: Error de calibración esperado del modelo en prueba < 0.03. *(Resultado: 0.035, no cumplido; ver quickstart y model card.)*
- **SC-004**: El 100 % de las cifras de la model card coincide con el reporte generado.
- **SC-005**: El modelo pesa < 5 MB.

## Assumptions

- El dataset de la spec 003 (`rain_hourly` v1.0.0) está construido localmente; en CI los tests usan datos sintéticos.
- El servicio de predicción adopta el nuevo modelo en la spec 006; el Backend adapta sus entradas en la spec 007.
- Fuera de alcance: búsqueda exhaustiva de hiperparámetros, modelos de deep learning, predicción por ventanas de varias horas.
