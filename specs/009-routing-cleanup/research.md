# Research: Routing service — limpieza

## R1. Hallazgos al leer el código actual

| ID | Hallazgo | Evidencia |
|---|---|---|
| H-10 | Regresor de intensidad con *rolling* que incluye el objetivo, elevación inventada y `probability = intensity × 25` | `train_rain_model.py`, `domain/rain_model.py` |
| H-11 | Si Open-Meteo falla se predice sobre "promedio de Medellín" (22 °C, 75 %, 60 %, 1.5 m/s) | `weather_service.py::_get_open_meteo_data` |
| H-12 | Una única `_mdva_cache_time` para todas las claves | `weather_service.py::_get_mdva_prediction` |
| H-30 | El viento de Open-Meteo `current` llega en km/h y se divide por 3.6 sin pedir unidades; el payload es el del modelo v1 (6 variables, sin `time_utc`) | `weather_service.py` |
| H-31 | `traffic_factor = 1.5` en vías primarias y `grade` siempre 0 (sin elevaciones): constantes sin fuente | `networkx_routing_service.py::get_weight` |
| H-32 | Tiempo = longitud / (11.11 m/s / penalty) y pasos cada `len(path)//10` nodos con "Continuar hacia el norte" | `_build_route`, `_generate_nav_steps` |
| H-33 | `ox.distance.nearest_nodes` en un grafo sin proyectar exige `scikit-learn` (BallTree); es la única razón para mantenerlo tras quitar el regresor | OSMnx 2.1 `distance.py` |
| H-34 | `/route/multi` promedia `rain_factor`/`rain_probability` entre tramos y la alerta usa umbral `>= 0.70` (RF-10 dice `> 0.70`) | `use_cases.py::execute_multi_stop` |

## R2. Señal de lluvia

- **Decision**: `RainSignalClient.signal(lat, lon)` → Open-Meteo Forecast (`hourly=<9 variables>`, `forecast_days=1`, `timezone=GMT`, `wind_speed_unit=ms`, `temperature_unit=celsius`, `precipitation_unit=mm`), verifica `hourly_units`, toma la hora UTC en curso y llama `POST /v2/predict` con `time_utc` + 9 variables. Devuelve `RainSignal(probability, alert_level, model_version, time_utc, available=True)`; ante cualquier error, `RainSignal.unavailable()` y un `logging.warning`.
- **Rationale**: misma fuente, variables y unidades que el entrenamiento y el Backend (constitución VI); las features las calcula el ML API con `mdva` (P2). La lista de las 9 variables se fija en el cliente, igual que en el Backend; si el contrato cambia, el ML API responde 422 y la señal queda no disponible.
- **Alternatives considered**: instalar `mdva` en el routing service para descargar con `mdva.openmeteo` (cambia el *build context* y arrastra pandas/sklearn); pedirle al Backend la señal (dependencia circular).

## R3. Caché

- **Decision**: `TTLCache` propio (diccionario `clave → (valor, instante)` + reloj inyectable), 5 min, clave `"{lat:.2f},{lon:.2f}"`; las señales no disponibles **no** se cachean.
- **Alternatives considered**: `cachetools.TTLCache` (dependencia nueva para 15 líneas; constitución: justificar cada dependencia).

## R4. Velocidades y tiempos

- **Decision**: al cargar el grafo, si una arista no tiene `travel_time`, `ox.add_edge_speeds(G)` + `ox.add_edge_travel_times(G)` y se guarda el grafo de nuevo en caché. Costo: `fastest` = `travel_time × factor_RF10`; `shortest` = `length`. Bicicleta: `length / (min(speed_kph, 15) / 3.6)`.
- **Factor uniforme**: con un factor constante el argmin de `fastest` no cambia; se aplica para que los tiempos devueltos incluyan la lluvia (R-30). La variación espacial es la spec 010.

## R5. Nodo más cercano sin scikit-learn

- **Decision**: `NearestNodeIndex` con arreglos `numpy` de lat/lon de los nodos y distancia equirectangular vectorizada (error < 0.1 % a escala del valle, ~100 k nodos en < 5 ms). Permite quitar `scikit-learn` (SC-004).

## R6. Pasos de navegación

- **Decision**: se agrupan aristas consecutivas con el mismo `name` (o `highway` si no hay nombre); cada paso: "Continúa por {nombre} {distancia}" con giro ("Gira a la izquierda/derecha", "Continúa") según el cambio de rumbo entre grupos (> 30°). Duración = suma de `travel_time` del grupo (× factor), de modo que los pasos suman la duración total.

## R7. Retiro de v1 en el ML API

- **Decision**: se eliminan `/predecir/{modelo}`, `/predecir/ambos`, `/monitorear/trayecto`, `load_models()` y `models/{random_forest,regresion_logistica}.pkl`. `/` y `/health` se conservan (RF-03), apuntando al modelo v2. Enmienda del charter a 2.0.0 (MAJOR: cambia RF-17, RF-22 y RF-23 de §4).
