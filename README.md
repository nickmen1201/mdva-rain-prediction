# Monitoreo de Variables Ambientales (MVA)

Aplicación web de planificación de viajes y monitoreo ambiental para el área metropolitana del Valle de Aburrá (Medellín, Colombia). Integra predicción de lluvia con modelos de Machine Learning entrenados con datos locales del SIATA, enrutamiento ambiental y recomendaciones instructivas de movilidad en tiempo real.

**Equipo:** Camilo Ardila · Santiago Martínez · Nicolás Meneses · Luis Ángel Seoanes  
**Periodo:** 13/02/2026 – 04/05/2026 · 5 sprints quincenales

---

## Tabla de contenido

1. [Descripción general](#descripción-general)
2. [Stack tecnológico](#stack-tecnológico)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Requisitos previos](#requisitos-previos)
5. [Ejecución con Docker (recomendado)](#ejecución-con-docker-recomendado)
6. [Verificación de servicios](#verificación-de-servicios)
7. [API y endpoints](#api-y-endpoints)
8. [Desarrollo local (sin Docker)](#desarrollo-local-sin-docker)
9. [Base de datos](#base-de-datos)
10. [Datos](#datos)
11. [Modelos ML](#modelos-ml)
12. [CI/CD](#cicd)
13. [Documentación técnica](#documentación-técnica)
14. [Troubleshooting](#troubleshooting)

---

## Descripción general

MVA es una webapp mobile-first que combina:

- **Predicción de lluvia** — dos modelos scikit-learn (Random Forest AUC=0.82, Regresión Logística F1=0.78) entrenados con datos históricos del SIATA y Open-Meteo para el Valle de Aburrá.
- **Enrutamiento ambiental** — grafo vial OSMnx/NetworkX ponderado por condiciones climáticas.
- **Integración Google Cloud** — Directions API (ruta), Geocoding API (búsqueda de lugares), Weather API (condiciones actuales), Maps JS API (mapa interactivo).
- **Alertas instructivas** — niveles Verde / Amarillo / Rojo con tiempo de viaje ajustado por lluvia (factores ×1.00 / ×1.20 / ×1.35).
- **Navegación 3D** — vista de navegación paso a paso con cámara inclinada y capa de calor meteorológico.
- **Autenticación JWT** — registro y login de usuarios con hash bcrypt.

El stack completo corre en Docker Compose con un solo comando.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite, nginx (Docker), Google Maps JS API |
| Backend | Java 21, Spring Boot 3.4.2, JOOQ 3.19.18, Flyway, JWT |
| ML Service | Python 3.11, FastAPI, scikit-learn 1.8.0 |
| Routing Service | Python 3.11, FastAPI, OSMnx, NetworkX |
| Base de datos | PostgreSQL 16 |
| Infraestructura | Docker Compose, GitHub Actions (CI/CD parcial) |

---

## Estructura del repositorio

```
Monitoreo-de-variables-ambientales/      (Cookiecutter Data Science v2)
├── docker-compose.dev.yml  docker-compose.prod.yml   ← Orquestación de los 5 servicios
├── data/                    ← raw / interim / processed / external (no se versiona)
├── docs/                    ← Informe técnico, manuales y planes de sprint
├── models/                  ← Modelos entrenados (random_forest.pkl, regresion_logistica.pkl)
├── notebooks/               ← Exploración (convención <n>.<m>-<iniciales>-<descripcion>)
├── references/              ← Informe del curso y wiki en PDF
├── reports/figures/         ← Figuras generadas
├── mdva/                    ← Paquete de ciencia de datos (config de rutas, entrenamiento)
├── services/
│   ├── ml_api/              ← FastAPI de predicción de lluvia (puerto 8081)
│   └── routing_api/         ← FastAPI de enrutamiento OSMnx + NetworkX (puerto 8000)
├── apps/
│   ├── backend/             ← Spring Boot + JOOQ + Flyway (puerto 8080)
│   └── frontend/            ← React + Vite servido con nginx (puerto 8090)
├── db/                      ← init-docker.sql, seeds/ (CSV) y scripts/
├── tests/e2e/               ← Smoke test de punta a punta del stack
├── specs/  .specify/        ← Spec-Driven Development (constitución, charter y specs)
```

---

## Requisitos previos

- **Docker Desktop** instalado y corriendo (único requisito para el stack completo).
- Para desarrollo local del frontend: Node.js 24+ y npm 11+.
- Para regenerar código JOOQ: JDK 21 (no necesario si solo usas Docker).

---

## Ejecución con Docker (recomendado)

```bash
# Desde la raíz del repositorio
docker compose -f docker-compose.dev.yml up --build
```

Los servicios arrancan en orden por healthchecks:
```
postgres → ml-service → routing-service → backend → frontend
```

> El primer arranque puede tardar **5-10 minutos**: descarga de imágenes base, compilación del JAR de Spring Boot y descarga del grafo OSM del Valle de Aburrá.

Para detener y eliminar volúmenes:
```bash
docker compose -f docker-compose.dev.yml down -v
```

---

## Verificación de servicios

Una vez levantado el stack, verifica que todo responde:

| Servicio | URL | Verificación |
|---|---|---|
| Frontend | http://localhost:8090 | Pantalla de login/planificación |
| Backend health | http://localhost:8080/actuator/health | `{ "status": "UP" }` |
| Swagger UI | http://localhost:8080/swagger-ui.html | Documentación interactiva |
| ML Service health | http://localhost:8081/health | Modelos cargados |
| ML Service docs | http://localhost:8081/docs | Swagger FastAPI |
| Routing Service health | http://localhost:8000/health | Grafo listo |
| Routing Service docs | http://localhost:8000/docs | Swagger FastAPI |
| PostgreSQL | `psql -h localhost -p 5436 -U postgres -d mdva` | Conexión exitosa |

---

## API y endpoints

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register` | Registro de usuario nuevo |
| POST | `/api/auth/login` | Login — retorna JWT |

### Viajes

| Método | Ruta | HTTP | Descripción |
|---|---|---|---|
| POST | `/api/viajes/planificar` | 201 | Planifica viaje completo (ruta + ML + alerta) |
| GET | `/api/viajes/{id}` | 200/404 | Obtiene un viaje por ID |
| PATCH | `/api/viajes/{id}/finalizar` | 200 | Marca el viaje como finalizado |
| GET | `/api/viajes/usuario/{idUsuario}` | 200 | Historial de viajes del usuario |

### Clima

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/weather/current` | Condiciones actuales por coordenada (Open-Meteo independiente) |
| GET | `/api/weather/grid` | Datos de cuadrícula para capa de calor |

### Ubicaciones

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/locations/municipalities` | Lista de municipios del Valle de Aburrá |
| GET | `/api/locations/municipalities/{id}/communes` | Comunas de un municipio |
| GET | `/api/locations/communes/{id}/neighborhoods` | Barrios de una comuna |

### Ejemplo — Planificar un viaje

```bash
curl -X POST http://localhost:8080/api/viajes/planificar \
  -H "Content-Type: application/json" \
  -d '{
    "idUsuario": 1,
    "origen": {
      "lat": 6.2442,
      "lng": -75.5812,
      "displayName": "Medellín Centro"
    },
    "destino": {
      "lat": 6.1132,
      "lng": -75.6145,
      "displayName": "Itagüí"
    }
  }'
```

El microservicio ML también es accesible directamente:

```bash
curl -X POST http://localhost:8081/predecir/ambos \
  -H "Content-Type: application/json" \
  -d '{
    "temperatura_c": 18.5,
    "humedad_relativa_pct": 82.0,
    "cobertura_nubosa_pct": 75.0,
    "velocidad_viento_ms": 2.3,
    "hora": 14,
    "mes": 4
  }'
```

---

## Comandos de desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/) (instala Python 3.11 si hace falta) y Docker. Los objetivos del `Makefile` siguen la convención Cookiecutter Data Science v2; en Windows sin `make` se usa el comando equivalente.

| Objetivo | Comando equivalente | Qué hace |
|---|---|---|
| `make requirements` | `uv sync` · `uv sync --project services/ml_api` · `uv sync --project services/routing_api` | Entornos de los 3 proyectos Python desde sus lockfiles |
| `make lint` | `uv run ruff check .` · `uv run ruff format --check .` | Lint y formato |
| `make format` | `uv run ruff check --fix .` · `uv run ruff format .` | Corrige y formatea |
| `make test` | `uv run pytest` · `uv run --project services/ml_api pytest services/ml_api/tests` · `uv run --project services/routing_api pytest services/routing_api/tests` | Tests de Python |
| `make secrets` | `docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.30.1 git /repo --log-opts=HEAD` | Escaneo de secretos |
| `make up` / `make down` | `docker compose -f docker-compose.dev.yml up --build -d` / `down` | Stack de desarrollo |
| `make smoke` | `uv run python tests/e2e/smoke_stack.py` | Smoke test de punta a punta (con el stack arriba) |

La CI (`.github/workflows/`) corre lint, tests, escaneo de secretos y los builds del Backend y del Frontend en cada push.

## Desarrollo local (sin Docker)

### Backend

```bash
cd apps/backend
# Windows
.\gradlew.bat bootRun --args="--spring.profiles.active=dev"

# Linux/Mac
./gradlew bootRun --args="--spring.profiles.active=dev"
```

Requiere PostgreSQL corriendo en `localhost:5436` con la BD `mdva` inicializada (`db/init-docker.sql`).

### Frontend

```bash
cd apps/frontend
npm install
npm run dev    # http://localhost:5173
```

Variables necesarias en `apps/frontend/.env` (plantilla en `apps/frontend/.env.example`):
```
VITE_GOOGLE_MAPS_KEY=<tu_api_key>
VITE_API_BASE_URL=http://localhost:8080
```

### Regenerar código JOOQ

Con PostgreSQL corriendo en el puerto 5436:

```bash
cd apps/backend
.\gradlew.bat generateJooq   # Windows
./gradlew generateJooq        # Linux/Mac
```

---

## Base de datos

**Motor:** PostgreSQL 16  
**Puerto host:** 5436 (→ 5432 interno)  
**Base de datos:** `mdva`  
**Usuario:** `postgres` / **Password:** valor de `POSTGRES_PASSWORD` en tu `.env` local (desarrollo)

**Tablas principales:**

| Tabla | Descripción |
|---|---|
| `municipios` | 10 municipios del Valle de Aburrá |
| `comunas` | 21 comunas y corregimientos |
| `barrios` | 46 barrios |
| `tipos_vehiculo` | 11 tipos de vehículo |
| `tipos_motor` | 7 tipos de motor |
| `usuarios` | Cuentas de usuario con hash bcrypt |
| `vehiculos` | Flota de vehículos por usuario (placa colombiana validada) |
| `viajes` | Viajes planificados con ruta, condiciones ML y estado |

**Migraciones Flyway:**

| Versión | Descripción |
|---|---|
| V1 | Estado base (`init-docker.sql`) — tablas + datos seed |
| V2 | Agrega coordenadas lat/lng, nombre y distancia a `viajes` |

---

## Datos

El dataset de entrenamiento se reconstruye con un solo comando (`make data`, ~30 s con la caché de descargas) y queda en `data/processed/rain_hourly.parquet` (no versionado; sí lo están el contrato y los reportes).

| Aspecto | Detalle |
|---|---|
| Fuente | Open-Meteo, 2022–2025: *Historical Forecast* (variables de entrada, las mismas que se piden en vivo) y *ERA5* (precipitación de referencia), en UTC y con unidades explícitas |
| Ubicaciones | 13 estaciones SIATA del Valle de Aburrá → **455 832 filas** (13 × 35 064 horas), 0 descartadas |
| Etiqueta | `rain = precipitación ERA5 de la misma hora ≥ 0.5 mm/h`; tasa de lluvia 19.0 % |
| Calidad | Contrato declarativo `rain_hourly` v1 (`mdva/data_contract.py`): tipos, unidades, rangos, nulos, clave única y cobertura; una etapa que no lo cumple no se promueve. Resultado en [`reports/data_quality.json`](reports/data_quality.json) |
| Reproducibilidad | Manifiesto SHA-256 de las descargas; una segunda ejecución hace 0 descargas y produce la misma huella de contenido |

### Validación externa de la etiqueta (SIATA)

Los pluviómetros SIATA disponibles cubren solo un mes (7 jun – 7 jul de 2022), así que no se usan para entrenar sino para medir qué tan fiel es la etiqueta (`make validate-labels` → [`reports/metrics/label_validation.json`](reports/metrics/label_validation.json)):

- **Umbral calibrado sin fuga**: con la primera mitad del mes, por igualación de frecuencias, 0.5 mm/h en ERA5 reproduce la tasa observada en SIATA (24.0 % vs. 21.4 %). La segunda mitad solo se usa para medir.
- **Acuerdo hora a hora bajo** (validación, 11 estaciones, 3 891 horas): kappa 0.05 a 1 h, 0.13 a 3 h y 0.18 a 6 h (F1 0.23 → 0.57). El pronóstico crudo de Open-Meteo obtiene valores muy parecidos (kappa 0.08 / 0.15 / 0.19).
- **Limitación de resolución**: ERA5 tiene celdas de ~25 km; 8 de las 13 estaciones caen en la misma celda, de modo que la etiqueta describe lluvia "en la zona" y no en un punto. Las métricas del modelo se leen frente a esta referencia, no frente a un pluviómetro.
- Exclusiones: la estación 205 no tiene minutos con calidad 1 y la 206 solo 9 horas comparables (< 250).

---

## Modelos ML

Los modelos se sirven vía `http://localhost:8081` (FastAPI).

| Modelo | Archivo | AUC | F1 | Uso |
|---|---|---|---|---|
| Random Forest | `models/random_forest.pkl` | 0.82 | ~0.78 | Decisión principal de alerta |
| Regresión Logística | `models/regresion_logistica.pkl` | — | 0.78 | Referencia complementaria |

- Entrenados con datos del SIATA + Open-Meteo (Valle de Aburrá).
- Versión scikit-learn **1.8.0** fijada en `services/ml_api/uv.lock` (la de los `.pkl`) — no cambiar sin re-entrenar.
- Mejora desde línea base: F1 0.65 → 0.78 (+20%).

> Nota: uno de los dos modelos puede no estar en el repositorio por tamaño. El ML Service arranca en modo tolerante a fallos y retorna HTTP 503 si se solicita un modelo no cargado.

---

## CI/CD

Configurado parcialmente con GitHub Actions (`./github/workflows/release.yml`). El pipeline está en progreso (HU025); algunos workflows se marcan como fallidos en pushes regulares.

---

## Documentación técnica

| Documento | Descripción |
|---|---|
| [docs/informe-tecnico.md](docs/informe-tecnico.md) | Arquitectura, esquema de BD, flujo de datos, decisiones técnicas |
| [docs/manual-usuario.md](docs/manual-usuario.md) | Guía de uso con flujos paso a paso y escenarios cotidianos |
| [docs/manual-pruebas.md](docs/manual-pruebas.md) | Casos de prueba, resultados de validación ML y pruebas piloto UX |
| [docs/sprints/sprint-3-documentacion.md](docs/sprints/sprint-3-documentacion.md) | Documentación detallada del Sprint 3 (Camilo Ardila) |

---

## Troubleshooting

**El routing-service tarda mucho en arrancar**  
Es normal en el primer arranque: descarga el grafo OSM del Valle de Aburrá y puede tardar 2-5 minutos. El healthcheck tiene `start_period: 120s`. Monitorea con `docker compose logs routing-service`.

**El backend falla al conectarse a la BD**  
Verifica que el contenedor `mdva-postgres` pasó su healthcheck (`pg_isready`). El backend depende del healthcheck, no solo del arranque del contenedor.

**Error de JOOQ: clase no encontrada**  
Regenera el código JOOQ con `./gradlew generateJooq` y reconstruye el backend.

**`POST /api/viajes/planificar` devuelve 502**  
Verifica que `mdva-ml` está corriendo: `curl http://localhost:8081/health`. Si retorna 503, el modelo `.pkl` no está disponible en disco.

**Frontend no carga el mapa (pantalla en blanco)**  
Verifica que `VITE_GOOGLE_MAPS_KEY` tiene un valor válido en `.env.production` antes del build de Docker.

**El gradlew falla con "bad interpreter" en Linux**  
El archivo `gradlew` tiene line endings CRLF. El Dockerfile lo corrige automáticamente con `sed`. Si ejecutas fuera de Docker en Linux: `sed -i 's/\r$//' gradlew && chmod +x gradlew`.

**Puerto 5436 en uso**  
El mapeo es no estándar para evitar conflictos con instalaciones locales de PostgreSQL. Si el puerto 5436 también está ocupado, cambia el mapeo en `docker-compose.dev.yml` y actualiza `build.gradle.kts` → `generateJooq` URL.
