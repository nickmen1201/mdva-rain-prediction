# Features del modelo de lluvia (contrato v1.1.0)

Única definición en código: [`mdva/features.py`](../mdva/features.py). La usan tanto el entrenamiento como el servicio de predicción; `tests/test_features.py` verifica la paridad entre ambos caminos y que esta tabla coincida con el código.

**Qué predice el modelo**: si en la celda de reanálisis que contiene un punto del Valle de Aburrá caerá lluvia apreciable (≥ 0.5 mm) en una hora dada (ver [specs/003](../specs/003-openmeteo-dataset/research.md)).

**Entradas**: el instante UTC objetivo, 9 variables del pronóstico de Open-Meteo para ese punto y esa hora, 8 valores del **mismo** pronóstico en las horas vecinas (ventana) y la latitud/longitud del punto; en las mismas unidades en entrenamiento (pronósticos archivados) y en producción (pronóstico en vivo, que trae la serie horaria completa).

Versiones: **1.0.0** (spec 004) = features 1–13, usado por el modelo 1.0.0. **1.1.0** (spec 012) agrega 14–24 porque el estudio de modelado mostró que mejoran el log loss en validación cruzada temporal en más de un error estándar y, para la ubicación, también en validación espacial dejando una celda ERA5 fuera (`reports/metrics/rain_classifier/study/study.json`, `feature_candidates` y `spatial_cv`).

| # | Feature | Origen | Unidad | Transformación | Por qué |
|---|---|---|---|---|---|
| 1 | `temperature_2m` | temperatura a 2 m | °C | identidad | modula la convección y la capacidad de humedad del aire |
| 2 | `relative_humidity_2m` | humedad relativa a 2 m | % | identidad | cercanía a la saturación en superficie |
| 3 | `dew_point_depression` | temperatura − punto de rocío | °C | diferencia | saturación en una sola variable; evita la colinealidad de usar el punto de rocío crudo |
| 4 | `cloud_cover` | nubosidad total | % | identidad | condición necesaria (no suficiente) para llover |
| 5 | `wind_u` | velocidad y dirección del viento a 10 m | m/s | `−v·sin(dir)` | componente zonal; la dirección en grados es circular (0° = 360°) |
| 6 | `wind_v` | velocidad y dirección del viento a 10 m | m/s | `−v·cos(dir)` | componente meridional; vale 0 en calma |
| 7 | `pressure_msl` | presión a nivel del mar | hPa | identidad | sistemas sinópticos y ondas tropicales |
| 8 | `precipitation_log1p` | precipitación pronosticada | mm/h | `log(1 + x)` | el pronóstico numérico es el baseline; el modelo aprende a corregirlo (MOS). Distribución muy sesgada |
| 9 | `cape_log1p` | energía potencial convectiva disponible | J/kg | `log(1 + x)` | potencial de tormentas convectivas, típicas del valle. Distribución muy sesgada |
| 10 | `hour_sin` | instante UTC → hora local de Bogotá | — | `sin(2π·h/24)` | ciclo diurno (lluvias de tarde y de madrugada) sin discontinuidad a medianoche |
| 11 | `hour_cos` | instante UTC → hora local de Bogotá | — | `cos(2π·h/24)` | ídem |
| 12 | `month_sin` | instante UTC → mes local | — | `sin(2π·(m−1)/12)` | régimen bimodal de lluvias (abril–mayo, octubre–noviembre) |
| 13 | `month_cos` | instante UTC → mes local | — | `cos(2π·(m−1)/12)` | ídem |
| 14 | `precipitation_prev2_log1p` | precipitación pronosticada en t−2 h | mm/h | `log(1 + x)` | el pronóstico acierta la lluvia pero no siempre la hora: la ventana absorbe errores de *timing* |
| 15 | `precipitation_prev1_log1p` | precipitación pronosticada en t−1 h | mm/h | `log(1 + x)` | ídem |
| 16 | `precipitation_next1_log1p` | precipitación pronosticada en t+1 h | mm/h | `log(1 + x)` | ídem |
| 17 | `precipitation_next2_log1p` | precipitación pronosticada en t+2 h | mm/h | `log(1 + x)` | ídem |
| 18 | `cloud_cover_prev1` | nubosidad en t−1 h | % | identidad | evolución de la nubosidad (desarrollo o disipación) |
| 19 | `cloud_cover_next1` | nubosidad en t+1 h | % | identidad | ídem |
| 20 | `cape_prev1_log1p` | CAPE en t−1 h | J/kg | `log(1 + x)` | la convección responde a la inestabilidad acumulada, no solo a la de la hora |
| 21 | `cape_next1_log1p` | CAPE en t+1 h | J/kg | `log(1 + x)` | ídem |
| 22 | `precipitation_5h_log1p` | suma de precipitación pronosticada t−2…t+2 | mm/5 h | `log(1 + Σ)` | señal de "evento de lluvia" robusta al desfase horario |
| 23 | `latitude` | latitud del punto | ° | identidad | gradientes climatológicos dentro del valle (laderas y norte/sur); rango del contrato 6.0–6.6 |
| 24 | `longitude` | longitud del punto | ° | identidad | ídem; rango −75.8 a −75.2 (fuera del valle → 422) |

## Validación de entradas

Se rechazan (con el campo y la regla en el mensaje): campos faltantes (incluida cualquier hora de la ventana: nunca se rellenan), nulos, valores no numéricos, valores fuera del rango físico del contrato de datos e instantes sin zona horaria. Los rangos descartan valores imposibles, pero **no** detectan unidades equivocadas (p. ej. viento en km/h cabe en el rango en m/s); las unidades se garantizan pidiéndolas explícitamente a la fuente y verificando las que declara.

## Variables descartadas

| Variable | Motivo |
|---|---|
| Lluvia observada de la hora anterior (`precip_lag_1h_mm` del modelo original) | No existe una fuente en tiempo real equivalente a la de entrenamiento; era la feature dominante del modelo anterior (61 % de importancia) y en producción llegaba en 0 |
| Probabilidad de precipitación del pronóstico | No existe en el histórico de pronósticos |
| Identificador de estación | Memorizaría las 13 estaciones y no serviría para otros puntos del valle |
| *(Latitud y longitud, descartadas en 1.0.0)* | Se descartaron por el riesgo de memorizar las 5 celdas de la etiqueta. En 1.1.0 se adoptaron porque la validación espacial (entrenar sin una celda y evaluar en ella) mostró que **sí** generalizan a celdas no vistas |
| Punto de rocío crudo | Casi colineal con temperatura y humedad; se usa la depresión del punto de rocío |
| Hora y mes enteros del cliente | Se derivan del instante UTC dentro del módulo; el cliente no puede enviar una hora en la zona equivocada |
