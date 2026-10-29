# Model card — rain_classifier 1.0.0

> Generada automáticamente por `mdva.modeling.model_card` desde `metadata.json` y
> `reports/metrics/rain_classifier/1.0.0/metrics.json`. No editar a mano.

## Qué predice

Probabilidad calibrada de que en la celda de reanálisis ERA5 que contiene un punto del Valle de Aburrá caiga
lluvia apreciable (≥ 0.5 mm) en una hora dada, a partir del pronóstico de
Open-Meteo para ese punto y esa hora (13 features, contrato v1.0.0;
ver `docs/features.md`).

**Uso previsto**: alertas de lluvia para planificar trayectos (VERDE < 0.4,
AMARILLO ≤ 0.7, ROJO > 0.7).
**No** es un pronóstico de intensidad ni de lluvia en un punto exacto.

## Modelo

- Base: `HistGradientBoostingClassifier` `{'learning_rate': 0.1, 'max_leaf_nodes': 15, 'max_iter': 400, 'l2_regularization': 1.0}`, elegido por log loss en validación entre
  17 candidatos.
- Calibración: ninguna. En el sub-split de validación (ajuste ene–jun, evaluación jul–dic de 2024) las probabilidades nativas tuvieron el menor log loss (none 0.3246, isotonic 0.3291, sigmoid 0.3259).
- Tamaño: 0.74 MB · scikit-learn 1.8.0 ·
  semilla 42.

## Datos

| Split | Periodo (UTC) | Filas | Tasa de lluvia |
|---|---|---|---|
| Entrenamiento | 2022-01-01 → 2023-12-31 (sin jun–jul 2022) | 208,728 | 19.2 % |
| Validación | 2024-01-02 → 2024-12-31 | 113,880 | 15.7 % |
| Prueba | 2025-01-02 → 2025-12-31 | 113,568 | 21.5 % |

13 estaciones SIATA como ubicaciones (5 celdas ERA5 distintas). Huella del dataset: `57133164d885fd2e…`.

## Desempeño en prueba (2025, usado una sola vez)

IC 95 % por bootstrap en bloques de días (B = 500).

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | BSS vs climatología | ECE |
|---|---|---|---|---|---|---|
| **Modelo** | 0.825 [0.810, 0.840] | 0.581 | 0.1264 [0.116, 0.137] | 0.401 | 0.096 | 0.0346 |
| Regresión logística | 0.786 [0.770, 0.803] | 0.515 | 0.1359 [0.124, 0.147] | 0.428 | 0.028 | 0.0241 |
| Pronóstico crudo | 0.702 [0.688, 0.716] | 0.398 | 0.1557 [0.144, 0.167] | 0.486 | -0.114 | 0.0298 |
| Climatología | 0.768 [0.745, 0.791] | 0.494 | 0.1398 [0.127, 0.153] | 0.446 | 0.000 | 0.0278 |
| Persistencia (no desplegable) | 0.815 [0.804, 0.826] | 0.566 | 0.1247 [0.118, 0.133] | 1.723 | 0.107 | 0.1248 |

- ¿Supera a la climatología? sí (IC 95 % de la diferencia < 0 en Brier y log loss).
- ¿Supera al pronóstico crudo? sí (IC 95 % de la diferencia < 0 en Brier y log loss).
- ¿Supera a la regresión logística? sí (IC 95 % de la diferencia < 0 en Brier y log loss).
- Diferencia de Brier modelo − climatología: -0.0135
  [-0.017, -0.009].
- Validación (2024): ROC-AUC 0.865, Brier 0.0945.

## Calibración y niveles de alerta (prueba)

ECE = 0.0346 (≥ 0.03).
Curva de confiabilidad: `reports/figures/rain_classifier_reliability.png`.

| Nivel | % de horas | Llueve dentro del nivel |
|---|---|---|
| VERDE | 85.2 % | 14.2 % |
| AMARILLO | 11.6 % | 59.6 % |
| ROJO | 3.1 % | 78.1 % |

- Alerta ≥ AMARILLO: precisión 0.635, sensibilidad 0.435.
- Alerta ROJO: precisión 0.781, sensibilidad 0.113.

## Validación externa contra pluviómetros SIATA (jun–jul 2022, fuera del entrenamiento)

7,834 horas-estación; llueve en el pluviómetro en el 19.4 %.

| Puntaje | ROC-AUC frente a la lluvia medida |
|---|---|
| Modelo | 0.508 |
| Precipitación pronosticada (cruda) | 0.536 |
| Precipitación de referencia ERA5 (la etiqueta) | 0.532 |

Kappa del modelo al umbral AMARILLO: 0.037.

## Limitaciones

- La etiqueta es reanálisis (ERA5, ~25 km), no lluvia medida: el modelo predice lluvia **de la celda**. Frente a
  pluviómetros, la concordancia horaria es baja con cualquier fuente de malla (ver `reports/metrics/label_validation.json`).
- Las 13 estaciones caen en 5 celdas: hay menos observaciones independientes que filas.
- La tasa de lluvia cambia entre años (15.7 % en validación,
  21.5 % en prueba); la calibración se ajustó en un año más seco que el de prueba.
- Transparencia metodológica: durante el desarrollo se comparó una vez, sobre el año de prueba, el efecto de distintas
  estrategias de calibración. La decisión final (sin calibración posterior) se tomó con evidencia solo de validación
  (`specs/005-model-training/research.md`, R10), pero la prueba ya no es estrictamente "no vista" para esa decisión.
- Los pronósticos archivados corresponden a horizontes cortos; para horas lejanas el pronóstico de entrada es menos
  preciso y el desempeño puede ser menor.
