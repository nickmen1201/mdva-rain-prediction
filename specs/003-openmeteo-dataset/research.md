# Research: Dataset reproducible de lluvia (Open-Meteo) con validación externa SIATA

Análisis exploratorio hecho el 2026-10-28 contra las APIs reales; los números se reproducen en la implementación (`mdva/label_validation.py`) y quedan en `reports/metrics/label_validation.json`.

## R1. Fuentes y endpoints

- **Decision**:
  - Features: Historical Forecast API (`historical-forecast-api.open-meteo.com/v1/forecast`), modelo por defecto (`best_match`), variables `temperature_2m, relative_humidity_2m, dew_point_2m, cloud_cover, wind_speed_10m, wind_direction_10m, pressure_msl, precipitation, cape`.
  - Referencia de lluvia (etiqueta): Archive API (`archive-api.open-meteo.com/v1/archive`), `models=era5`, `precipitation`.
- **Rationale**: las 9 variables existen en el forecast en vivo y en el histórico 2022 con 0 % de nulos (verificado), así que entrenamiento e inferencia comparten fuente (constitución VI). `precipitation_probability` no existe en el histórico y queda excluida. ERA5-Land devolvió nulos para la celda de Medellín.
- **Alternatives considered**: Archive (reanálisis) como fuente de features (es lo que hacía el modelo anterior; no coincide con lo que llega en producción, H-04).

## R2. Volumen y estrategia de descarga

- **Decision**: una petición por fuente y por año con las 13 ubicaciones (coordenadas separadas por comas): 2 fuentes × 4 años = 8 peticiones. Unidades explícitas (`temperature_unit=celsius`, `wind_speed_unit=ms`, `precipitation_unit=mm`) y `timezone=GMT`.
- **Rationale**: medido: un año completo para 13 ubicaciones pesa 7.0 MB (forecast, 23 s) y 2.7 MB (ERA5, 9 s). Muy por debajo de los límites gratuitos (600/min, 5 000/h, 10 000/día).
- **Reintentos**: hasta 5 intentos ante 429 o 5xx, respetando `Retry-After` y, si no viene, con espera de 15, 30, 60 y 120 s; timeout de 300 s. La primera ejecución real (2026-10-28) recibió 429 en la tercera petición pesada: el límite es por minuto y pondera ubicaciones × variables × días, así que esperas de pocos segundos no bastaban.

## R3. Almacenamiento por etapa

- **Decision**:
  - `data/raw/openmeteo/{forecast,era5}/{año}.json`: respuesta tal cual, escrita de forma atómica (archivo temporal + renombrado). `data/raw/MANIFEST.json` registra URL, fecha de descarga y SHA-256 de cada archivo crudo, incluidos los CSV de SIATA.
  - `data/interim/openmeteo_{forecast,era5}.parquet`: formato largo (ubicación, hora UTC, variables).
  - `data/processed/rain_hourly.parquet`: forecast + referencia + etiqueta.
- **Rationale**: Parquet conserva tipos y zona horaria (CSV no). Idempotencia: si el archivo crudo existe y su SHA-256 coincide con el manifiesto, no se descarga.
- **Determinismo (FR-012, SC-002)**: además del SHA-256 del archivo, el reporte guarda una huella del contenido (`pandas.util.hash_pandas_object` sobre el DataFrame ordenado), estable aunque cambie la versión del escritor de Parquet.
- **Nueva dependencia**: `pyarrow`: motor de Parquet para pandas; la stdlib no lee ni escribe Parquet.

## R4. Umbral de la etiqueta

Comparación de pluviómetros SIATA (hora local → UTC, horas con ≥ 50 minutos válidos; "llueve" = ≥ 0.1 mm en la hora) contra la referencia, 2022-06-07 → 2022-07-07, 7 834 horas-estación:

| Referencia | Ventana | Umbral ref. | kappa | Frecuencia SIATA | Frecuencia ref. |
|---|---|---|---|---|---|
| ERA5 | 1 h | 0.1 mm | 0.021 | 0.19 | 0.56 |
| ERA5 | 1 h | **0.5 mm** | **0.052** | 0.19 | **0.22** |
| ERA5 | 1 h | 1.0 mm | 0.032 | 0.19 | 0.11 |
| ERA5 | 6 h | 1.0 mm | 0.208 | 0.53 | 0.46 |
| Pronóstico | 1 h | 0.5 mm | 0.052 | 0.19 | 0.15 |
| Pronóstico | 6 h | 1.0 mm | 0.191 | 0.53 | 0.43 |

- **Decision**: etiqueta horaria con umbral elegido por **igualación de frecuencias** en la primera mitad del mes de SIATA (el umbral de la rejilla {0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0} mm/h cuya frecuencia ERA5 queda más cerca de la de SIATA). En el análisis exploratorio, con el mes completo, sale 0.5 mm/h; el valor final lo fija el código y queda registrado en el reporte y en la configuración.
- **Rationale**: con 0.1 mm/h ERA5 marca lluvia más del doble de veces que los pluviómetros (sesgo de llovizna conocido del reanálisis). Igualar frecuencias es una calibración estándar; separar las mitades evita evaluar con los mismos datos con que se eligió el umbral.
- **Limitación documentada**: la concordancia horaria punto a punto es baja con cualquier fuente de malla (kappa ≤ 0.06 a 1 h; ≈ 0.2 a 6 h). La lluvia en el valle es convectiva y muy local, y las 13 estaciones caen en solo 5 celdas ERA5 (8 en el pronóstico). El modelo de la spec 005 aprende a predecir la lluvia **de la celda**, y la validación externa mide cuánto se aleja eso de la lluvia en un punto.
- **Alternatives considered**: ventanas de 3 a 6 h (mejor kappa, pero el producto razona por hora: alertas, pronóstico horario, monitoreo); 0.1 mm/h (estándar de "hora húmeda", pero aquí casi aleatorio).

## R5. Zona horaria de SIATA

- **Decision**: los timestamps de SIATA son hora local de Colombia (UTC−5) y se convierten a UTC sumando 5 h.
- **Rationale**: el ciclo diurno con los timestamps tal cual tiene picos a las 14 h y a la 1–2 h, coherente con la convección vespertina y las lluvias nocturnas de Medellín. Leídos como UTC, el pico caería a las 9 h locales. El desfase de máxima concordancia con ERA5 (0 h) no se usa: ERA5 adelanta varias horas el ciclo diurno de la convección tropical, así que ese máximo refleja el sesgo del reanálisis, no la zona horaria. La validación reporta los desfases −8…+8 h para transparencia.

## R6. Contrato de datos

- **Decision**: contrato declarativo en `mdva/data_contract.py` (columna → tipo, unidad, rango, nulabilidad; claves únicas; cobertura mínima) con una función `validate(df, contract) -> QualityReport` que acumula todas las violaciones y lanza `DataContractError` si hay alguna. Versión del contrato en el propio módulo (`DATASET_CONTRACT_VERSION = "1.0.0"`), exportada también a [contracts/rain_hourly.v1.json](contracts/rain_hourly.v1.json).
- **Rationale**: cubre exactamente las reglas de FR-004 sin dependencias nuevas y deja el resultado de cada regla en el reporte.
- **Alternatives considered**: pandera (compatibilidad con pandas 3.1 no garantizada); Great Expectations (sobredimensionado).

## R7. Reglas y umbrales de calidad

| Regla | Umbral |
|---|---|
| Unidades de la respuesta | iguales a las pedidas (`°C`, `%`, `m/s`, `°`, `hPa`, `mm`, `J/kg`) |
| Cobertura por ubicación | ≥ 99 % de las 35 064 horas del periodo |
| Nulos por variable y ubicación | ≤ 1 % (no se imputan; las filas con nulos no reciben etiqueta) |
| Unicidad | (ubicación, hora UTC) única |
| Rangos físicos | temperatura −5…45 °C; humedad 0…100 %; punto de rocío −20…35 °C; nubosidad 0…100 %; viento 0…60 m/s; dirección 0…360°; presión 950…1 050 hPa; precipitación 0…200 mm/h; CAPE 0…10 000 J/kg |
| SIATA | calidad = 1, precipitación ≥ 0; hora válida si tiene ≥ 50 minutos |

## R8. Interfaz de línea de comandos

- **Decision**: módulos ejecutables con `argparse` y `logging` de la stdlib (`python -m mdva.dataset`, `python -m mdva.label_validation`); objetivos `make data` y `make validate-labels`.
- **Rationale**: la plantilla CCDS v2 sugiere typer y loguru, pero la constitución exige justificar dependencias frente a la stdlib, y aquí no aportan nada esencial.

## R9. Ubicaciones

- **Decision**: catálogo de las 13 estaciones (código, nombre, municipio, latitud, longitud) en `data/external/siata_stations.csv`, derivado del CSV crudo de SIATA y versionado en el manifiesto. El pipeline lo genera si falta.
- **Rationale**: es la única fuente de coordenadas de estaciones disponible.
