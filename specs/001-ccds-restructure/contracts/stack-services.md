# Contract: Servicios del stack de desarrollo

Contrato externo que la reestructura **no** puede cambiar (FR-003, FR-005). Solo cambia la columna "Contexto de build".

| Servicio Compose | Contenedor | Puerto host → contenedor | Health | Contexto de build (antes → después) | Dockerfile |
|---|---|---|---|---|---|
| `postgres` | `mdva-postgres` | 5436 → 5432 | `pg_isready -U postgres -d mdva` | imagen `postgres:16-alpine` (sin cambio) | — |
| `ml-service` | `mdva-ml` | 8081 → 8081 | `GET /health` | `./Data-science` → `.` (raíz) | `services/ml_api/Dockerfile` |
| `routing-service` | `mdva-routing` | 8000 → 8000 | `GET /health` | `./Data-science/enrutamiento_ambiental` → `./services/routing_api` | `Dockerfile` |
| `backend` | `mdva-backend` | 8080 → 8080 | `GET /api/health` | `./Backend` → `./apps/backend` | `Dockerfile` |
| `frontend` | `mdva-frontend` | 8090 → 80, 8443 → 443 | — | `./Frontend` → `./apps/frontend` | `Dockerfile` |

**Volúmenes** (nombre efectivo con `name: monitoreo-de-variables-ambientales`):
`monitoreo-de-variables-ambientales_postgres_data`, `monitoreo-de-variables-ambientales_routing_graph_cache`.

**Montaje de inicialización de BD**: `./DB/init-docker.sql` → `./db/init-docker.sql` (mismo destino `/docker-entrypoint-initdb.d/01-init.sql`).

**Variables de entorno**: sin cambios respecto al commit `a47c3c5` (se leen del `.env` local).

Clasificación del cambio: **aditivo / sin ruptura** para los consumidores (puertos, endpoints y health idénticos); interno para el equipo (rutas de build).
