# MDVA — Monitoreo de Variables Ambientales

Sistema de navegación inteligente para el Valle de Aburrá (Medellín) que combina predicción de lluvia con ML, enrutamiento OSM y análisis climático en tiempo real.

## Arquitectura (4 servicios)

| Servicio | Tecnología | Puerto host |
|---|---|---|
| PostgreSQL 16 | postgres:16-alpine | 5436 |
| ML Service | FastAPI + Python 3.11 | 8081 |
| Routing Service | FastAPI + OSMnx + Python 3.11 | 8000 |
| Backend | Spring Boot 3.4.2 + Java 21 + JOOQ | 8080 |
| Frontend | React 19 + Vite + nginx | 8090 |

## Levantar el stack completo

```bash
docker compose -f docker-compose.dev.yml up --build
```

**Nota:** El primer arranque del `routing-service` puede tardar 2–10 minutos porque descarga el grafo OSM del Valle de Aburrá (~500MB). El grafo se cachea en un volumen Docker `routing_cache` para reinicios posteriores.

## Desarrollo local (sin Docker)

```bash
# 1. PostgreSQL (puerto 5432 local)
# 2. ML Service
uv run --project services/ml_api uvicorn main:app --app-dir services/ml_api --port 8081

# 3. Routing Service
cd services/routing_api && uv run uvicorn main:app --port 8000

# 4. Backend
cd apps/backend && ./gradlew bootRun --args='--spring.profiles.active=dev'

# 5. Frontend
cd apps/frontend && npm install && npm run dev
```

## Flujo de un viaje (integración completa)

```
PlanificarViaje.jsx
  → POST /api/viajes/planificar
    → SmartRoutingServiceImpl → GET routing-service:8000/api/v1/route (OSMnx + NetworkX)
    → WeatherMLServiceImpl   → GET open-meteo.com (clima actual)
                             → POST ml-service:8081/predecir/ambos (Random Forest + Reg. Logística)
    → TripPlannerOrchestrator → ajusta tiempo según prob. lluvia
    → ViajeRepositoryImpl    → persiste en PostgreSQL
  ← TripResponseDTO (polyline, alerta VERDE/AMARILLO/ROJO, tiempo ajustado)
ResultadoViaje.jsx → MapaRuta + AlertaClimatica
```

## Variables de entorno clave

| Variable | Default local | Docker |
|---|---|---|
| `ML_SERVICE_URL` | `http://localhost:8081` | `http://ml-service:8081` |
| `SMART_ROUTING_API_URL` | `http://localhost:8000/api/v1` | `http://routing-service:8000/api/v1` |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/mdva` | `jdbc:postgresql://postgres:5432/mdva` |
| `JWT_SECRET` | (dev hardcoded) | Usar GitHub Secrets en producción |

## Modelos ML (models/)

- `random_forest.pkl` — AUC 0.82, **usado para decisiones** (umbral verde/amarillo/rojo)
- `regresion_logistica.pkl` — AUC 0.78, backup/validación cruzada
- **scikit-learn fijado en 1.8.0** en `services/ml_api/uv.lock` — cambiar la versión rompe los `.pkl` (el routing service usa 1.9.1 con un modelo serializado en 1.8.0; se elimina en la spec 009)
- Dependencias Python: un `pyproject.toml` + `uv.lock` por proyecto (raíz `mdva`, `services/ml_api`, `services/routing_api`); comandos en el `Makefile`

### Reglas de ajuste de tiempo por lluvia

| Prob. Random Forest | Nivel | Factor |
|---|---|---|
| < 40% | VERDE | ×1.00 |
| 40–70% | AMARILLO | ×1.20 |
| > 70% | ROJO | ×1.35 + sugerir alterna si dist > 5km |

## Predicción de lluvia (WeatherMLService)

1. Llama Open-Meteo API (gratuito, sin API key) para obtener temperatura, humedad, cobertura nubosa, viento
2. Transforma: hora y mes con encoding cíclico (sin/cos)
3. POST a FastAPI `/predecir/ambos` → 2 predicciones (RF + RL)
4. Si hay precipitación activa (>0.1mm), fuerza `llueve=true`

## Enrutamiento (services/routing_api/)

Arquitectura DDD con 3 tipos de ruta:
- **fastest** — optimizada por tráfico + lluvia (`rain_sensitivity=1.0`)
- **shortest** — distancia bruta
- **dryest** — evita zonas húmedas (`rain_sensitivity=3.0`, solo si prob > 10%)

El Backend usa la primera opción (fastest). El modelo de lluvia interno (`cache/rain_model.joblib`) es independiente del modelo en `models/` — es un regressor de intensidad, no un clasificador binario.

## Base de datos (Flyway migrations)

- `V1` — schema base (usuarios, vehículos, viajes, geografía)
- `V2` — agrega `lat_origen`, `lng_origen`, `lat_destino`, `lng_destino`, `nombre_origen`, `nombre_destino`, `distancia_metros`
- `V3` — elimina columnas heredadas `id_barrio_origen/destino` (ejecutar cuando se limpie historial)

Regenerar código JOOQ tras cambios de schema:
```bash
cd apps/backend && ./gradlew generateJooq
```

## Autenticación

- JWT almacenado en `localStorage` (key: `token`)
- `userId` almacenado en `localStorage` (key: `userId`) — usado para historial
- El token incluye `username` e `id` del usuario como claims
- Todos los endpoints `/api/**` requieren `Authorization: Bearer {token}`

## Comandos útiles

```bash
# Logs en tiempo real
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f routing-service

# Conectar a PostgreSQL
psql -h localhost -p 5436 -U postgres -d mdva

# Swagger UI
http://localhost:8080/swagger-ui.html   # Backend
http://localhost:8081/docs              # ML Service
http://localhost:8000/docs              # Routing Service
```

## Seguridad (pendiente para producción)

- La contraseña de PostgreSQL, el JWT secret y la API key de Google se leen del `.env` local (gitignored); ver `.env.example`
- El JWT secret de dev está hardcodeado — usar `JWT_SECRET` env var
- Tokens JWT en localStorage — considerar cookies HTTPOnly en producción
- `CORS allow_origins=["*"]` en routing-service — restringir en producción
