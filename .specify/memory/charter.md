# Charter del proyecto MDVA

> Contexto obligatorio para toda spec de este repositorio: diagnóstico, estructura objetivo,
> mandatos de cambio y requisitos funcionales a preservar. Está **subordinado** a
> `.specify/memory/constitution.md`: si chocan, gana la constitución.

- **Versión:** 1.1.0 (ver registro de cambios al final)
- **Objetivo de la refactorización:** convertir MDVA en un proyecto de portafolio de **Ciencia de Datos / ML** reproducible, metodológicamente defendible y con la estructura **Cookiecutter Data Science v2 (CCDS v2)**, sin perder la funcionalidad de producto que ya existe y sin depender de APIs de pago.

---

## 0. Diagnóstico de partida

Hallazgos verificados en el código al 2026-10-28. Cada uno tiene una regla correctiva en §3.

| ID | Hallazgo | Evidencia | Severidad |
|---|---|---|---|
| H-01 | **API key de Google Maps commiteada** en el repo y en el historial | `Frontend/.env`, `Frontend/.env.production`, `docker-compose.dev.yml:108`, `Backend/src/main/resources/application-dev.yml:25`, `README.md`, `CLAUDE.md` | Crítica |
| H-02 | **Entrenamiento no reproducible**: los CSV de SIATA no están en el repo y la ruta de respaldo es absoluta a la máquina de un compañero | `Data-science/train_models.py` (`C:/Users/Luis Seoanes/...`), igual en `train_rain_model.py` | Crítica |
| H-03 | **Train/serve skew de unidades**: el viento se entrena en **km/h** (Open-Meteo Archive sin `wind_speed_unit`) pero se nombra `velocidad_viento_ms` y en inferencia se envía en **m/s** | `train_models.py` vs `WeatherMLServiceImpl.java` (`wind_speed_unit=ms`, `/3.6`) y `weather_service.py` (`/3.6`) | Alta |
| H-04 | **Train/serve skew de fuente**: se entrena con reanálisis Open-Meteo Archive (un solo punto, La Candelaria) y se infiere con Google Weather (`inferCloudCover` = nubosidad *inferida*) u Open-Meteo Forecast | `train_models.py`, `WeatherMLServiceImpl.predictRainForLocation` | Alta |
| H-05 | **Feature dominante ausente en inferencia**: `precip_lag_1h_mm` explica ~61 % de la importancia del RF; en entrenamiento es el promedio SIATA del Valle de la hora anterior, en inferencia es la precipitación *actual* de Open-Meteo o **0 por defecto** (forecast horario, monitoreo de trayecto, routing service) | Importancias medidas sobre `random_forest.pkl`; payloads en `WeatherMLServiceImpl` (forecast), `TripMonitorServiceImpl`, `weather_service.py` | Alta |
| H-06 | **Desfase horario**: el entrenamiento usa `America/Bogota`; el Backend y el routing service calculan `hora` con `LocalDateTime.now()` / `datetime.now()` en contenedores sin `TZ` (UTC) → hora desplazada 5 h | `docker-compose.*.yml` (sin `TZ`), `WeatherMLServiceImpl`, `weather_service.py` | Alta |
| H-07 | **Evaluación débil**: sin holdout temporal, CV de 3 folds sin respetar el tiempo, sin baselines (persistencia/climatología), sin PR-AUC/Brier, métricas no persistidas. Las cifras publicadas se contradicen (AUC 0.82 en README/CLAUDE.md vs 0.91 en el commit `c333f81`) | `train_models.py`, `README.md`, `CLAUDE.md` | Alta |
| H-08 | **Probabilidades no calibradas usadas como umbrales de negocio**: `class_weight="balanced"` sesga las probabilidades hacia arriba y luego el Backend las corta en 0.40/0.70. Además `llueve` del ML usa `predict()` (umbral 0.5), inconsistente con esos umbrales | `train_models.py`, `Data-science/main.py::predecir`, `TripPlannerOrchestrator` | Media-Alta |
| H-09 | **Ruta "dryest" ficticia**: la penalización de lluvia es un escalar calculado solo en el origen y multiplica a todas las aristas por igual → el argmin no cambia y "dryest" ≡ "fastest" | `networkx_routing_service.py::get_weight` | Alta |
| H-10 | **Regresor de intensidad con fuga y features falsas**: las ventanas `rolling` incluyen el valor objetivo actual (leakage); `elevation_approx = 1500 + (station_id % 50) * 20` es inventada; en inferencia `rolling_*` siempre es 0 y la elevación se calcula con otra fórmula; `probability = intensity * 25` es arbitraria; métricas reportadas sobre train | `train_rain_model.py`, `domain/rain_model.py` | Alta |
| H-11 | **Datos fabricados silenciosamente**: si Open-Meteo falla, el routing service devuelve valores "promedio de Medellín" y predice sobre ellos sin avisar | `weather_service.py::_get_open_meteo_data` | Media |
| H-12 | **Bug de caché**: un único `_mdva_cache_time` global para todas las claves → entradas viejas se sirven como frescas | `weather_service.py::_get_mdva_prediction` | Media |
| H-13 | **Versiones inconsistentes**: los `.pkl` están serializados con scikit-learn **1.8.0**; `CLAUDE.md`/README dicen 1.4.2; el routing service no fija versiones | `requirements.txt` (ambos), metadatos de los pickles | Media |
| H-14 | **Binarios pesados en git**: `random_forest.pkl` (67 MB), `rain_model.joblib` (4.6 MB), PDFs, `TIC1DB.backup` | `git ls-files` | Media |
| H-15 | **Código muerto / stubs**: `SiataLiveService` devuelve `{1: 0.0, 2: 0.5}` fijo; `OpenWeatherMap base_url` sin uso; script duplicado `scripts/train_rain_model.py`; bloque de elevación vacío en `OSMnxMapRepository` | archivos citados | Baja |
| H-16 | **Cero tests y cero CI para Python**; la CI solo cubre el Backend | `.github/workflows/ci.yml` | Media |
| H-17 | **Documentación desactualizada y duplicada**: dos README casi idénticos del ML service con puertos distintos (8000 vs 8081) y nombre de archivo erróneo (`regresi_n_log_stica.pkl`); `CLAUDE.md` describe una carpeta `enrutamiento/` que no existe | `Data-science/README.md`, `Data-science/models/README.md`, `CLAUDE.md` | Baja |
| H-19 | **Google Cloud inutilizable**: el proyecto dueño de la key tiene la facturación desactivada; Directions, Geocoding, Weather y Maps JS responden `REQUEST_DENIED`/403. Planificar viaje, clima actual, monitoreo y el mapa del Frontend están caídos | Smoke test del 2026-10-28 (`docker compose up`, `POST /api/viajes/planificar` → 500) | Crítica |
| H-20 | **Datos SIATA originales perdidos**: los 185 CSV ya no existen. Solo hay 2 CSV de 13 estaciones y 1 mes (2022-06-07 → 2022-07-07, resolución 1 min); el "clean" conserva códigos de calidad anómalos (1567, 15345) | `precipitacion_siata_plano.csv`, `clean_precipitacion_siata_plano.csv` | Alta |
| H-18 | **Modelo "espacial" sin features espaciales**: el clasificador predice lluvia promedio del Valle con features de un solo punto, pero se usa para un heatmap de 81 puntos | `train_models.py`, `/api/weather/predict-grid` | Media (documentar) |

---

## 1. Principios específicos del proyecto

Complementan la constitución; ante conflicto, gana la constitución.

**P1 — Reproducibilidad total.** Desde un clon limpio, `make data && make features && make train && make evaluate` reconstruye datos procesados, modelos y métricas. Prohibidas las rutas absolutas y las rutas fuera del repo. Semillas fijas y registradas.

**P2 — Una sola definición de features.** Existe **un único** módulo (`mdva/features.py`) que transforma datos crudos en la matriz de features. Entrenamiento e inferencia lo importan. Duplicar la lógica de features en Java, en el routing service o en un notebook está prohibido; los demás servicios envían variables crudas con unidades explícitas.

**P3 — Contrato de datos explícito.** Cada feature declara nombre, unidad (SI), rango válido, fuente y zona horaria en un esquema versionado (`mdva/schemas.py`). La API valida contra ese esquema y rechaza (422) valores fuera de rango.

**P4 — Evaluación honesta.** Ningún número de desempeño se publica sin: split temporal, comparación con baselines, intervalo de incertidumbre y archivo de métricas generado por código. Nunca se reporta desempeño sobre datos de entrenamiento.

**P5 — Sin datos inventados.** Ninguna feature se fabrica (elevaciones sintéticas, fallbacks "promedio", probabilidades = intensidad × constante). Si un insumo falta, el sistema lo declara (`degraded=true` / error) en lugar de inventarlo.

**P6 — Secretos fuera del repo.** Ninguna credencial en archivos versionados. Configuración por variables de entorno con `.env.example` como única plantilla.

**P7 — Artefactos pesados fuera de git.** Los datos se regeneran con `make data` (Open-Meteo) y nunca se versionan en git. Un modelo solo puede versionarse en git si pesa < 5 MB; si no, se publica como asset de GitHub Release con checksum SHA-256. Cada modelo va acompañado de `metadata.json` y `model_card.md`.

**P8 — Honestidad sobre la autoría.** El README distingue claramente qué partes fueron trabajo de equipo (4 autores) y cuáles son contribución propia del responsable del portafolio, en particular en el componente de ML.

**P9 — Cambios quirúrgicos y verificables.** Cada spec define criterios de aceptación ejecutables (tests). Refactorizar sin tests que pasen antes y después está prohibido. Nada especulativo: no se agrega funcionalidad que no esté en §4 o en una spec aprobada.

---

## 2. Estructura objetivo (Cookiecutter Data Science v2)

El repositorio raíz **es** el proyecto CCDS v2. El paquete de ciencia de datos se llama `mdva`. Los componentes de producto (servicios y apps) viven en subcarpetas y **consumen** el paquete, nunca al revés.

```
Monitoreo-de-variables-ambientales/
├── LICENSE
├── Makefile                  ← make data | features | train | evaluate | lint | format | test | requirements | clean
├── README.md                 ← portada orientada a DS: problema, datos, método, resultados, demo, autoría
├── .specify/                ← constitución, charter y plantillas spec-kit
├── specs/                   ← una carpeta por spec (spec, plan, contratos, tareas)
├── pyproject.toml            ← paquete mdva, ruff, pytest; deps fijadas
├── requirements.txt          ← (o uv.lock) generado, versiones exactas
├── .env.example
├── dvc.yaml / dvc.lock       ← pipeline: data → features → train → evaluate
│
├── data/                     ← gitignored (salvo .gitkeep); versionado con DVC
│   ├── external/             ← Open-Meteo descargado, catálogos de estaciones SIATA
│   ├── raw/                  ← CSV SIATA pluviometría originales (inmutables)
│   ├── interim/              ← SIATA agregado por hora/estación, joins intermedios
│   └── processed/            ← dataset final de modelado (parquet)
│
├── docs/                     ← mkdocs; informes, manuales y planes de sprint movidos aquí
├── models/                   ← gitignored; <modelo>/<version>/{model.joblib, metadata.json, model_card.md}
├── notebooks/                ← convención CCDS: <n>.<m>-<iniciales>-<descripcion>.ipynb
│   ├── 1.0-nm-analisis-espacial-siata-vs-openmeteo.ipynb   (el notebook actual, renombrado)
│   ├── 2.0-nm-eda-pluviometria-siata.ipynb
│   └── 3.0-nm-evaluacion-y-calibracion.ipynb
├── references/               ← diccionario de datos SIATA/Open-Meteo, informe PDF del curso
├── reports/
│   ├── figures/              ← generadas por mdva/plots.py
│   └── metrics/              ← metrics.json por modelo/versión (generado, no editado a mano)
│
├── mdva/                     ← paquete Python CCDS v2
│   ├── __init__.py
│   ├── config.py             ← rutas (PROJ_ROOT, DATA_DIR…), constantes, carga de .env, logging (loguru)
│   ├── schemas.py            ← contrato de features (P3), compartido con services/ml_api
│   ├── dataset.py            ← descarga/carga SIATA + Open-Meteo, limpieza, agregación horaria, etiquetas
│   ├── features.py           ← build_features(): ÚNICA fuente de feature engineering (P2)
│   ├── modeling/
│   │   ├── __init__.py
│   │   ├── train.py          ← entrena, calibra, serializa + metadata
│   │   ├── evaluate.py       ← métricas, baselines, curvas, metrics.json
│   │   └── predict.py        ← carga de modelo + predict_proba usando features.py
│   └── plots.py
│
├── services/
│   ├── ml_api/               ← FastAPI delgado sobre mdva.modeling.predict (antes Data-science/main.py)
│   │   ├── main.py, Dockerfile, tests/
│   └── routing_api/          ← antes Data-science/enrutamiento_ambiental (mantiene capas DDD)
│       ├── domain/, application/, infrastructure/, presentation/, main.py, Dockerfile, tests/
│
├── apps/
│   ├── backend/              ← antes Backend/ (Spring Boot, sin cambios de estructura interna)
│   └── frontend/             ← antes Frontend/ (React + Vite)
│
├── db/
│   ├── init-docker.sql
│   ├── seeds/                ← municipios.csv, comunas.csv, barrios.csv
│   └── scripts/webscraper_municipios.py
│
├── tests/                    ← pytest del paquete mdva (features, dataset, contrato, skew)
├── docker-compose.dev.yml
├── docker-compose.prod.yml
└── .github/workflows/
    ├── ci-backend.yml        ← (el ci.yml actual, con working-directory apps/backend)
    ├── ci-python.yml         ← ruff + pytest + smoke test de ml_api
    └── release.yml
```

**Reglas de estructura**

- E-01: Los Dockerfiles de `services/ml_api` y `services/routing_api` usan como *build context* la raíz del repo (para poder instalar `mdva`), con `.dockerignore` que excluya `data/`, `apps/`, `notebooks/`.
- E-02: Los notebooks son para exploración y comunicación; **ningún** servicio ni script importa de un notebook. Lógica reutilizable descubierta en un notebook se mueve a `mdva/`.
- E-03: Los notebooks se guardan con salidas limpias o con salidas ligeras (sin datasets embebidos); las figuras finales salen de `mdva/plots.py` hacia `reports/figures/`.
- E-04: `config.py` es el único lugar donde se definen rutas; ningún módulo construye rutas con `Path(__file__).parent / ".." / ".."`.
- E-05: Los nombres de módulos, funciones y variables de Python se mantienen en el idioma ya usado por el equipo (español para dominio, inglés aceptado para términos técnicos), pero de forma consistente dentro de cada módulo.

---

## 3. Mandatos de cambio

### 3.1 Eliminación de archivos innecesarios

| ID | Acción | Archivo(s) | Motivo |
|---|---|---|---|
| D-01 | ✅ Hecho (commit `a47c3c5`): secretos leídos de `.env` local; historial del repo nuevo depurado | `Frontend/.env`, `Frontend/.env.production`, `docker-compose.dev.yml`, `application-dev.yml` | H-01. La key queda obsoleta al eliminar Google (spec 007, 008, 011) |
| D-02 | Eliminar | `Data-science/enrutamiento_ambiental/scripts/train_rain_model.py` | Wrapper duplicado |
| D-03 | Eliminar | `Data-science/enrutamiento_ambiental/train_rain_model.py`, `domain/rain_model.py`, `cache/rain_model.joblib` | H-10. Ver R-20 |
| D-04 | Eliminar | `Data-science/enrutamiento_ambiental/infrastructure/siata_live_service.py` | Stub sin uso (H-15) |
| D-05 | Eliminar | `Data-science/README.md`, `Data-science/models/README.md` | Duplicados y erróneos (H-17); se reemplazan por `services/ml_api/README.md` + `model_card.md` |
| D-06 | Sacar de git (mover a DVC / Release) | `Data-science/models/*.pkl` | H-14, P7 |
| D-07 | Eliminar | `DB/TIC1DB.sql`, `DB/TIC1DB.backup` | Flyway (`V1`–`V6`) es la fuente de verdad del esquema |
| D-08 | Eliminar del índice (ya están en `.gitignore`) | `Backend/.idea/`, `Backend/.claude/`, `.vscode/settings.json` | Configuración local de IDE |
| D-09 | Renombrar | `Backend/dockerignore` → `apps/backend/.dockerignore` | Sin el punto, Docker lo ignora |
| D-10 | Mover a `references/` (o eliminar) | `Informe_Proyecto_MVA (1).pdf`, `Backend/wiki/GENERAL.pdf` | Binarios fuera de la raíz; nombre con espacios/paréntesis |
| D-11 | Mover a `docs/` | `Informe_Tecnico.md`, `Manual_Pruebas.md`, `Manual_Usuario.md`, `Backend/MDVA_Documentacion_Sprint3.md`, `Backend/TEST.md`, `implementationplans/*` | Raíz limpia; documentación en un solo lugar |
| D-12 | Evaluar y eliminar si no se usa | `railway.toml` (×4) | Solo si ya no se despliega en Railway; si se usa, se conserva junto a cada Dockerfile |
| D-13 | Fusionar en `CLAUDE.md` o eliminar | `CONTEXT.md` | Son pautas genéricas de agente, no contexto del proyecto |

> **Historial de git:** limpiar binarios y la key del historial (`git filter-repo`) reescribe commits de 4 autores. **No** se hace sobre el repo compartido sin acuerdo del equipo. Para el portafolio se recomienda un **fork propio** donde sí puede reescribirse.

### 3.2 Reorganización (mapa origen → destino)

| Origen | Destino |
|---|---|
| `Data-science/train_models.py` | partido en `mdva/dataset.py`, `mdva/features.py`, `mdva/modeling/train.py`, `mdva/modeling/evaluate.py` |
| `Data-science/main.py` | `services/ml_api/main.py` (solo HTTP; la lógica va a `mdva/modeling/predict.py` y `mdva/monitoring.py` si aplica) |
| `Data-science/notebooks/MDVA_analisis_espacial_prototipo.ipynb` | `notebooks/1.0-nm-analisis-espacial-siata-vs-openmeteo.ipynb` |
| `Data-science/enrutamiento_ambiental/` | `services/routing_api/` |
| `Data-science/Dockerfile`, `requirements.txt` | `services/ml_api/Dockerfile`; deps en `pyproject.toml` |
| `Backend/` | `apps/backend/` |
| `Frontend/` | `apps/frontend/` |
| `DB/Resources/*.csv` | `db/seeds/` |
| `DB/Resources/webscraper_municipios.py` | `db/scripts/` |
| `DB/init-docker.sql` | `db/init-docker.sql` |
| `.github/workflows/ci.yml` | `.github/workflows/ci-backend.yml` |

Tras mover: actualizar *build contexts* en ambos `docker-compose`, `working-directory` en CI, rutas en README y `CLAUDE.md`.

### 3.3 Refactor de código

#### A. Datos y etiquetas (`mdva/dataset.py`)

- R-01: **Fuente principal: Open-Meteo** (sin API key). `make data` descarga features y precipitación horaria del Valle de Aburrá, de forma idempotente y con caché en `data/raw/openmeteo/`. Los 2 CSV de SIATA (H-20) se colocan en `data/raw/siata/` con manifiesto de checksums y se usan **solo como validación externa** de la etiqueta (concordancia lluvia Open-Meteo vs pluviómetros reales), nunca para entrenar.
- R-02: Eliminar `except Exception: pass`; las estaciones descartadas se registran con motivo (log + `reports/data_quality.json`: estaciones leídas, descartadas, % calidad≠1, cobertura temporal).
- R-03: Definir la etiqueta formalmente en una spec: hoy es *"promedio del Valle ≥ 0.1 mm/h"*, lo que diluye lluvias locales. La spec debe elegir y justificar (p. ej. *"≥ X % de estaciones activas registran ≥ 0.1 mm/h"* o etiqueta por zona) y documentar la tasa de positivos resultante.
- R-04: Toda marca de tiempo se normaliza a `America/Bogota` de forma explícita (tz-aware) al cargar; se documenta la zona horaria original de SIATA.
- R-05: Las features de entrenamiento se obtienen de la **misma fuente que en inferencia**: *Open-Meteo Historical Forecast API* (pronósticos archivados, misma distribución que el forecast en vivo). La etiqueta proviene de la precipitación horaria de Open-Meteo; su limitación (no es observación directa) se cuantifica con R-01.
- R-06: Toda descarga de Open-Meteo fija unidades explícitas (`wind_speed_unit=ms`, `temperature_unit=celsius`) y valida que la respuesta las confirme (`hourly_units`).

#### B. Features (`mdva/features.py`, `mdva/schemas.py`)

- R-07: `build_features(df_crudo) -> DataFrame` es la única transformación; la usan `train.py` y `predict.py`. Las columnas salen en orden fijo definido en `schemas.FEATURES`.
- R-08: Los modelos se entrenan sobre `DataFrame` con nombres de columnas (no `.values`), de modo que scikit-learn valide nombres en inferencia.
- R-09: Separar dos tareas con contratos distintos (definirlo en spec):
  - **Nowcast** (`horizonte = 0 h`): admite `precip_lag_1h_mm`, solo si en inferencia existe una fuente equivalente a la de entrenamiento (idealmente SIATA en vivo, o la misma fuente usada al entrenar).
  - **Forecast** (`horizonte 1–6 h`, usado por `/api/weather/forecast`, `best-window` y monitoreo): **sin** features de lag no disponibles.
  Prohibido enviar `0` como relleno de una feature desconocida.
- R-10: Validación de rangos en `schemas.py` (p. ej. humedad 0–100, nubosidad 0–100, viento 0–60 m/s, hora 0–23, mes 1–12). Un viento > 60 debe fallar, lo que detecta envíos en km/h.

#### C. Entrenamiento y evaluación (`mdva/modeling/`)

- R-11: Split **temporal**: train / validación / test por bloques de fecha (test = último periodo completo, p. ej. último año). CV con `TimeSeriesSplit` (con *gap* ≥ 24 h para evitar autocorrelación).
- R-12: Baselines obligatorios en el mismo `metrics.json`: (a) climatología por hora×mes, (b) persistencia (si llovió en t−1), (c) regresión logística. El modelo elegido debe superar a los tres en el test; si no lo hace, se documenta.
- R-13: Métricas: ROC-AUC, **PR-AUC**, **Brier score**, log loss, curva de calibración, matriz de confusión en los umbrales de negocio (0.40 y 0.70), con IC por bootstrap. Todo a `reports/metrics/<modelo>/<version>/metrics.json` y figuras a `reports/figures/`.
- R-14: **Calibración**: si se usa `class_weight`, calibrar (`CalibratedClassifierCV`, isotónica o sigmoide, sobre validación temporal). Los umbrales 0.40/0.70 de §4 se aplican a probabilidades calibradas, y su elección queda justificada en la model card (trade-off de falsas alarmas vs lluvias no avisadas).
- R-15: Test de **skew**: comparar distribución de cada feature en train vs muestras reales de inferencia (Open-Meteo forecast/Google) y reportarlo (`reports/metrics/skew.json`).
- R-16: Cada modelo serializado lleva `metadata.json`: versión del modelo, hash del dataset, rango de fechas, lista y orden de features con unidades, versión de scikit-learn/Python, semilla, métricas de test, umbral(es). Y `model_card.md` con uso previsto, limitaciones (incl. H-18) y sesgos.
- R-17: Reducir el tamaño del modelo si no afecta métricas (p. ej. `max_depth`, `n_estimators`, o `HistGradientBoostingClassifier`); la elección se decide con datos en el notebook `3.0`, no por intuición.
- R-18: Fijar versiones exactas (`scikit-learn==1.8.0` o la que se elija) en un único lugar; el servicio verifica al arrancar que la versión instalada coincide con `metadata.json` y falla si no.

#### D. Servicio ML (`services/ml_api`)

- R-19: Carga de modelos en `lifespan` (no al importar el módulo); `/health` reporta versión de modelo y `ready`.
- R-20: `llueve` y `etiqueta` se derivan del umbral configurado del modelo (metadata), no de `predict()` con 0.5. La respuesta incluye `version_modelo`, `calibrado: bool` y `tarea: nowcast|forecast`.
- R-21: Reemplazar `Field(example=...)` (deprecado en Pydantic 2) por `json_schema_extra`/`examples`; el request usa el esquema de `mdva/schemas.py`.
- R-22: Errores: no exponer `str(e)` de excepciones internas al cliente; loguear con traza y devolver mensaje genérico + `request_id`.
- R-23: `/monitorear/trayecto`: extraer reglas a una función pura testeada; eliminar la condición muerta `nivel_cambio != "CRITICO"`; documentar el tratamiento de deltas negativos. Mantener exactamente las reglas de §4.
- R-24: `/predecir/ambos` mantiene su contrato actual (lista RF + RL) por compatibilidad con el Backend.

#### E. Routing service (`services/routing_api`)

- R-25: Eliminar el regresor de intensidad (D-03) y sus derivados (`rain_intensity_avg`, `probability = intensity*25`, `elevation_factor`). La señal de lluvia proviene únicamente de `ml_api`.
- R-26: **Hacer real la ruta `dryest` o retirarla.** Para que sea real, la penalización debe variar **por arista**: interpolar a cada arista la probabilidad de lluvia de una grilla espacial (p. ej. la misma grilla de 81 puntos de `/api/weather/predict-grid`, o puntos Open-Meteo) y ponderar `length × (1 + rain_sensitivity × p_lluvia(arista))`. Criterio de aceptación: un test con grilla no uniforme demuestra que `dryest` ≠ `fastest`. Si no se implementa, `dryest` se elimina de la API y del Frontend.
- R-27: Si se mantiene la penalización por pendiente para bicicleta, el grafo debe tener elevaciones reales (`ox.elevation.add_node_elevations_raster` con un DEM SRTM en `data/external/`) y `ox.add_edge_grades`. Sin elevaciones, se elimina el factor (hoy `grade` es siempre 0).
- R-28: Corregir la caché (H-12): timestamp por clave (`dict[key] = (valor, ts)`) o `cachetools.TTLCache`.
- R-29: Eliminar los valores de fallback inventados (H-11, P5): si Open-Meteo o `ml_api` fallan, la ruta se calcula sin penalización y la respuesta lleva `clima_disponible=false`.
- R-30: El tiempo de viaje deja de ser `11.11 m/s / penalty` fijo: usar `ox.add_edge_speeds` + `ox.add_edge_travel_times` y aplicar el factor de lluvia sobre `travel_time`.
- R-31: Eliminar `base_url` de OpenWeatherMap y el parámetro `api_key` sin uso; `datetime.now(ZoneInfo("America/Bogota"))` en vez de `datetime.now()`.
- R-32: Fijar versiones en `pyproject.toml` (hoy `requirements.txt` sin versiones).
- R-33: CORS restringido a los orígenes configurados por variable de entorno.

#### F. Backend (cambios mínimos, solo los que afectan al ML)

- R-34: Usar `ZoneId.of("America/Bogota")` en el cálculo de `hora`/`mes` enviados al ML (`WeatherMLServiceImpl`, `TripMonitorServiceImpl`), y agregar `TZ=America/Bogota` a los servicios en ambos compose.
- R-35: Reemplazar Google Weather por Open-Meteo en todo el Backend (H-19), de modo que la fuente de inferencia coincida con la de entrenamiento (R-05); se elimina `inferCloudCover`.
- R-35b: Reemplazar Google Directions por el routing service propio (`/api/v1/route/spring`, ya diseñado como sustituto) y Google Geocoding por Nominatim (OSM), respetando su política de uso (User-Agent identificable, ≤ 1 req/s, caché).
- R-35c: Frontend: reemplazar Google Maps JS + Places por MapLibre GL + teselas OSM y autocompletado vía Backend (Nominatim). Se preservan heatmap, polyline, navegación con cámara inclinada y orientación del dispositivo.
- R-36: No enviar `precip_lag_1h_mm` cuando el modelo no lo usa (forecast) y no enviar ceros de relleno (R-09).
- R-37: ✅ Hecho (commit `a47c3c5`). Al retirar Google se elimina `GOOGLE_MAPS_API_KEY` de toda la configuración.

#### G. Calidad, tests y CI

- R-38: `ruff` (lint + format) configurado en `pyproject.toml`; `make lint` y `make format`.
- R-39: Tests mínimos de Python (`tests/` y `services/*/tests/`):
  - `test_features.py`: codificación cíclica, orden de columnas, rangos.
  - `test_contract.py`: las features que produce `predict.py` para un payload de ejemplo son idénticas a las de `train.py` para la fila equivalente (**anti-skew**).
  - `test_units.py`: un payload con viento en km/h típico (> 60) es rechazado.
  - `test_ml_api.py`: `TestClient` sobre `/health`, `/predecir/ambos`, `/monitorear/trayecto` con un modelo dummy.
  - `test_monitoring_rules.py`: tabla de casos de §4.4.
  - `test_routing_weights.py`: R-26.
- R-40: `ci-python.yml` corre ruff + pytest en cada PR; los tests de servicios no requieren descargar el grafo OSM (usar un grafo sintético pequeño).
- R-41: Logging con `loguru`/`logging` en vez de `print`.

#### H. Documentación

- R-42: `README.md` raíz reescrito para un lector de DS: problema → datos (SIATA + Open-Meteo, periodo, tamaño) → etiqueta → features → validación temporal → resultados vs baselines (tabla generada desde `metrics.json`) → calibración y umbrales → arquitectura del producto → cómo reproducir → limitaciones → autoría (P8).
- R-43: Actualizar `CLAUDE.md` a la nueva estructura y a las versiones reales; eliminar cifras que no salgan de `reports/metrics/`.
- R-44: Una sola fuente de verdad para métricas: README y model card **citan** `metrics.json`; prohibido escribir AUC a mano.

---

## 4. Requisitos funcionales que el sistema ya cumple y deben preservarse

Ninguna spec puede romper estos comportamientos sin enmendar este charter. Son la base de los tests de regresión.

### 4.1 Arquitectura y despliegue
- RF-01: Stack de 5 servicios levantable con `docker compose -f docker-compose.dev.yml up --build`.
- RF-02: Puertos host: PostgreSQL 5436, ML 8081, Routing 8000, Backend 8080, Frontend 8090.
- RF-03: Healthchecks: `GET /health` (ml_api y routing_api), `GET /api/health` (Backend).
- RF-04: El grafo OSM del Valle de Aburrá (10 municipios: Medellín, Bello, Itagüí, Envigado, Sabaneta, La Estrella, Caldas, Copacabana, Girardota, Barbosa; `network_type="drive"`) se descarga una vez y se cachea en el volumen `routing_cache`.
- RF-05: Swagger/OpenAPI disponible en los tres backends (`/swagger-ui.html`, `/docs`).
- RF-06: Esquema de BD gestionado por Flyway (`V1`–`V6`), con JOOQ regenerable vía `./gradlew generateJooq`.

### 4.2 Autenticación
- RF-07: `POST /auth/register` y `POST /auth/login` con bcrypt y JWT (claims `username`, `id`).
- RF-08: Todos los endpoints `/api/**` exigen `Authorization: Bearer {token}`; el Frontend guarda `token` y `userId` en `localStorage`.

### 4.3 Viajes y alertas
- RF-09: `POST /api/viajes/planificar`: ruta (routing_api) + predicción de lluvia (ml_api) + ajuste de tiempo + persistencia; responde polyline, alerta y tiempo ajustado. *(Hoy caído por H-19; se restablece sin Google.)*
- RF-10: Reglas de alerta sobre la probabilidad del Random Forest (o del modelo que lo reemplace, ya calibrado):

  | Probabilidad | Nivel | Factor de tiempo |
  |---|---|---|
  | < 0.40 | VERDE | ×1.00 |
  | 0.40 – 0.70 | AMARILLO | ×1.20 |
  | > 0.70 | ROJO | ×1.35 + sugerir ruta alterna si distancia > 5 000 m |

- RF-11: Si hay precipitación activa medida (> 0.1 mm), se fuerza `llueve=true`.
- RF-12: Rutas multi-parada (`POST /api/v1/route/multi`), paradas persistidas (`GET /api/viajes/{id}/paradas`, `PATCH /api/viajes/{id}/paradas/{orden}/finalizar`).
- RF-13: `PATCH /api/viajes/{id}/finalizar`, `GET /api/viajes/{id}`, historial `GET /api/viajes/usuario/{idUsuario}`.
- RF-14: Tipo de vehículo en el enrutamiento (`car`, `bike`); las rutas alternativas están siempre disponibles para el usuario (commit `0a5dfa5`).
- RF-15: Endpoints del routing service: `POST /api/v1/route`, `/route/multi`, `/route/spring` (compatible con el Backend), `/route/metrics`; pasos de navegación y polyline codificada.

### 4.4 Monitoreo en trayecto
- RF-16: `POST /api/viajes/{id}/posicion`, `GET /api/viajes/{id}/alertas`, `PATCH /api/viajes/{id}/alertas/{idAlerta}/leer`, `GET /api/viajes/{id}/alerta-actual`.
- RF-17: Snapshot de condiciones al iniciar (tabla `condiciones_snapshot`) y `POST /monitorear/trayecto` en ml_api con estas reglas:
  - `delta = p_actual − p_inicio`; `0.10 ≤ delta ≤ 0.25` → MODERADO; `delta > 0.25` → SIGNIFICATIVO; en otro caso ESTABLE.
  - Latencia del dato meteorológico > 15 min → sube un nivel (ESTABLE→MODERADO→SIGNIFICATIVO→CRITICO).
  - `p_actual > 0.85` → CRITICO (prevalece).

### 4.5 Clima y visualización
- RF-18: `GET /api/weather/current`, `GET /api/weather/forecast` (pronóstico horario, 6 h por defecto), `GET /api/weather/best-window` (mejor ventana de salida), `POST /api/weather/predict-grid` (grilla ≤ 81 puntos, TTL 180 s).
- RF-19: Caché de predicción puntual con TTL 180 s en el Backend.
- RF-20: Ubicaciones: `GET /api/locations/municipalities`, `/municipalities/{id}/communes`, `/communes/{id}/neighborhoods` (semillas en `db/seeds/`).
- RF-21: Frontend: rutas `/login`, `/register`, `/` (mapa de ciudad con heatmap), `/planificar`, `/viaje/:id`, `/viaje/:id/en-ruta` (navegación 3D con cámara inclinada y orientación del dispositivo), `/historial/:idUsuario`; tema claro/oscuro; UI mobile-first.

### 4.6 ML
- RF-22: `ml_api` expone `/predecir/{modelo}` (`random_forest`, `regresion_logistica`) y `/predecir/ambos`, con codificación cíclica de hora y mes.
- RF-23: El Random Forest (o su reemplazo justificado por R-12) es el modelo de decisión; la Regresión Logística se mantiene como baseline/validación cruzada.

---

## 5. Orden de specs (SDD)

Cada spec recorre specify → clarify → plan → tasks → analyze → implement, con commit por fase o tarea.

| # | Spec | Cubre |
|---|---|---|
| 001 | Reestructuración CCDS v2 (mover sin cambiar comportamiento) | §2, §3.1, §3.2 |
| 002 | Tooling Python, calidad y CI (uv, ruff, pytest, escáner de secretos) | R-38–R-41, constitución III |
| 003 | Dataset Open-Meteo reproducible + validación externa SIATA | R-01–R-06 |
| 004 | Contrato y módulo único de features | R-07–R-10 |
| 005 | Entrenamiento con validación temporal, baselines y calibración | R-11–R-18 |
| 006 | Refactor de ml_api (contract-first) | R-19–R-24 |
| 007 | Backend: clima con Open-Meteo, TZ y paridad de features | R-34–R-36, R-35 |
| 008 | Backend: rutas con routing service propio y geocodificación Nominatim | R-35b |
| 009 | Routing service: limpieza (regresor, caché, fallbacks, tiempos reales) | R-25, R-28–R-33 |
| 010 | Routing service: ruta `dryest` espacial real y elevaciones | R-26, R-27 |
| 011 | Frontend sin Google (MapLibre + Nominatim) | R-35c |
| 012 | Documentación de portafolio y model card | R-42–R-44, P8 |

---

## 6. Definición de "terminado" (global)

1. `make lint test` en verde; CI de Backend y de Python en verde.
2. Desde un clon limpio + datos en `data/raw/` (o `dvc pull`), `make train evaluate` reproduce `metrics.json` con diferencias < 0.005 en ROC-AUC.
3. `docker compose -f docker-compose.dev.yml up --build` levanta los 5 servicios y un viaje de punta a punta (RF-09) funciona.
4. `git grep -nE "AIza|camilo123|C:/Users"` no devuelve resultados y el stack corre sin ninguna API key.
5. Ningún archivo > 5 MB versionado en git (fuera de DVC).
6. Los requisitos de §4 tienen al menos un test o un caso en `docs/Manual_Pruebas.md` que los cubre.

---

## 7. Fuera de alcance

- Reescribir el Backend o el Frontend más allá de lo exigido en R-34–R-37, R-35b, R-35c y los cambios de rutas por la reestructuración.
- Agregar nuevas funcionalidades de producto.
- Despliegue en la nube (se conserva lo que ya existe; no se exige nada nuevo).

---

## 8. Gobernanza

- Las enmiendas se hacen por commit que modifica este archivo, incrementa la versión (SemVer: MAJOR si elimina un principio o un requisito de §4, MINOR si agrega, PATCH si aclara) y registra el cambio abajo.
- Toda spec cita los IDs (P-, H-, D-, R-, RF-) que implementa.

### Registro de cambios
- **1.0.0 (2026-10-28):** versión inicial (como `CONSTITUTION.md`).
- **1.1.0 (2026-10-28):** pasa a ser charter subordinado a `.specify/memory/constitution.md`; agrega H-19 (Google sin facturación) y H-20 (datos SIATA perdidos); fuente de datos Open-Meteo con SIATA como validación externa; retiro de Google (R-35, R-35b, R-35c); D-01 y R-37 hechos; nuevo orden de specs.
