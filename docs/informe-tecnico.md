# INFORME TÉCNICO
## Monitoreo de Variables Ambientales (MVA)
**Versión:** 1.0 · Sprint 5  
**Fecha:** 19/05/2026  
**Equipo:** Camilo Ardila · Santiago Martínez · Nicolás Meneses · Luis Ángel Seoanes

---

## 1. Descripción general del sistema

MVA es una aplicación web de monitoreo ambiental y enrutamiento diseñada para el área metropolitana del Valle de Aburrá (Medellín, Colombia). Integra predicción de lluvia basada en modelos de Machine Learning entrenados con datos locales del SIATA y Open-Meteo, enrutamiento sensible a condiciones ambientales y recomendaciones instructivas de movilidad en tiempo real.

El sistema está compuesto por cinco servicios independientes orquestados con Docker Compose, que se comunican a través de una red interna de Docker.

---

## 2. Arquitectura del sistema

### 2.1 Diagrama de capas y contenedores

```
┌──────────────────────────────────────────────────────────────────────┐
│  CAPA DE PRESENTACIÓN                                                │
│  Frontend React/Vite · nginx · Puerto host 8090                      │
│  Contenedor: mdva-frontend                                           │
│  - Vista de planificación de viaje (PlanificarViaje.jsx)             │
│  - Vista de resultado con mapa y alertas (ResultadoViaje.jsx)        │
│  - Vista de navegación en ruta 3D (EnRuta.jsx)                       │
│  - Vista de historial de viajes (HistorialViajes.jsx)                │
│  - Capa de calor meteorológico (WeatherHeatmapLayer.jsx)             │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ HTTP / REST (axios)
┌───────────────────────────▼──────────────────────────────────────────┐
│  CAPA DE APLICACIÓN                                                  │
│  Backend Spring Boot 3.4.2 · Java 21 · Puerto host 8080             │
│  Contenedor: mdva-backend                                            │
│  - Autenticación JWT (registro + login)                              │
│  - Endpoint /api/viajes/planificar (orquesta el flujo completo)      │
│  - Endpoint /api/weather/current y /api/weather/grid                 │
│  - Endpoints /api/locations/*                                        │
│  - Endpoints /api/auth/*                                             │
└──────────┬────────────────┬──────────────────┬───────────────────────┘
           │                │                  │
    PostgreSQL         FastAPI ML         FastAPI Routing
           │          (interno Docker)   (interno Docker)
┌──────────▼────────┐ ┌────▼──────────┐ ┌────▼─────────────────────────┐
│  BASE DE DATOS    │ │  ML SERVICE   │ │  ROUTING SERVICE              │
│  PostgreSQL 16    │ │  Python 3.11  │ │  Python 3.11                  │
│  Puerto host 5436 │ │  Puerto host  │ │  Puerto host 8000             │
│  Contenedor:      │ │  8081         │ │  Contenedor: mdva-routing     │
│  mdva-postgres    │ │  Contenedor:  │ │  - OSMnx + NetworkX           │
│  - 8 tablas       │ │  mdva-ml      │ │  - Grafo vial Valle de Aburrá │
│  - Flyway mig.    │ │  - RF (0.82)  │ │  - Enrutamiento ambiental     │
│  - 10 municipios  │ │  - RL (0.78)  │ │    ponderado por lluvia       │
└───────────────────┘ └───────────────┘ └──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│  CAPA DE INTEGRACIÓN EXTERNA                                         │
│  - Google Directions API  (ruta óptima, polyline, pasos)            │
│  - Google Geocoding API   (resolución de placeId → coordenadas)     │
│  - Google Weather API     (condiciones actuales por coordenada)     │
│  - Google Maps JS API     (mapa interactivo en frontend)            │
│  - SIATA / Open-Meteo     (datos históricos para entrenamiento ML)  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Orden de arranque (dependencias Docker Compose)

```
postgres (healthcheck: pg_isready)
  └─► ml-service (healthcheck: GET /health)
        └─► routing-service (healthcheck: GET /health)
              └─► backend (Spring Boot)
                    └─► frontend (nginx)
```

---

## 3. Tecnologías utilizadas por capa

### 3.1 Frontend

| Componente | Tecnología | Versión |
|---|---|---|
| Framework UI | React | 18.x |
| Build tool | Vite | 6.x |
| Servidor en producción | nginx | Alpine |
| Mapa interactivo | @vis.gl/react-google-maps | — |
| Enrutamiento SPA | react-router-dom | 7.x |
| Cliente HTTP | axios | — |
| API de mapa | Google Maps JavaScript API | — |

**Páginas principales:**

| Ruta | Componente | Descripción |
|---|---|---|
| `/` | `PlanificarViaje.jsx` | Formulario de planificación de viaje con autocompletado de Google Places y selección de vehículo |
| `/resultado/:id` | `ResultadoViaje.jsx` | Resultado del viaje: estadísticas, mapa con polyline, alerta climática |
| `/en-ruta/:id` | `EnRuta.jsx` | Navegación paso a paso con cámara 3D, capa de calor y botón de centrado |
| `/historial/:userId` | `HistorialViajes.jsx` | Listado de viajes históricos del usuario |
| `/login` | `Login.jsx` | Inicio de sesión |
| `/register` | `Register.jsx` | Registro de cuenta |
| `/mapa` | `MapaCiudad.jsx` | Vista panorámica del mapa con capa de calor meteorológico |

### 3.2 Backend

| Componente | Tecnología | Versión |
|---|---|---|
| Framework | Spring Boot | 3.4.2 |
| Lenguaje | Java | 21 (Eclipse Temurin Alpine) |
| ORM / Queries | JOOQ | 3.19.18 |
| Migraciones BD | Flyway | — |
| Seguridad | Spring Security + JWT | — |
| Build | Gradle (Kotlin DSL) | 9.2 |
| Reducción boilerplate | Lombok | — |
| Documentación API | springdoc-openapi (Swagger) | 2.7.0 |

### 3.3 Microservicio ML (Data-science)

| Componente | Tecnología | Versión |
|---|---|---|
| Framework API | FastAPI | — |
| Servidor ASGI | uvicorn | — |
| Lenguaje | Python | 3.11 |
| Modelos | scikit-learn | 1.4.2 (fijada) |
| Serialización | pickle | — |

### 3.4 Microservicio de Enrutamiento Ambiental

| Componente | Tecnología |
|---|---|
| Framework API | FastAPI |
| Grafos viales | OSMnx + NetworkX |
| Datos del grafo | OpenStreetMap (Valle de Aburrá) |
| Integración ML | HTTP → ml-service:8081 |
| Caché | Volumen Docker (`routing_graph_cache`) |

### 3.5 Base de datos

| Componente | Tecnología |
|---|---|
| Motor | PostgreSQL 16 Alpine |
| Migraciones | Flyway (baseline V1, incremental V2+) |
| Conexión desde backend | JOOQ + DataSource Spring |

### 3.6 Infraestructura

| Aspecto | Tecnología |
|---|---|
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions (parcial) |
| Gestión de código | Git / GitHub (repositorio privado único) |
| Gestión de tareas | Trello (Kanban) |

---

## 4. Flujo de datos — planificación de viaje

El flujo principal se dispara con `POST /api/viajes/planificar`.

```
Cliente (Frontend)
  │  TripRequestDTO { idUsuario, origen{lat,lng,displayName}, destino{lat,lng,displayName}, idVehiculo? }
  ▼
ViajeController
  ▼
ViajeUseCase.planificar()
  ├─[1]─► GoogleMapsService.resolveCoordinates()
  │         └─ Google Geocoding API  (si viene placeId en lugar de lat/lng directas)
  │
  ├─[2]─► GoogleMapsService.getOptimalRoute()
  │         └─ Google Directions API → { duraciónSeg, distanciaMetros, polyline, pasos[] }
  │
  ├─[3]─► WeatherMLService.predictRainForLocation(lat, lng)
  │         ├─ GET weather.googleapis.com/v1/currentConditions:lookup
  │         │    → { temperatura, humedad, viento, probabilidadLluvia }
  │         └─ POST http://ml-service:8081/predecir/ambos
  │              → { probabilidadRf, probabilidadRl, llueve }
  │
  ├─[4]─► TripPlannerOrchestrator.apply(ruta, prediccion, vehiculo)
  │         └─ Reglas de ajuste por lluvia y restricciones de vehículo
  │              → { tiempoAjustado, nivelAlerta, mensajeAlerta, sugerirRutaAlterna }
  │
  └─[5]─► ViajeRepository.save()
            └─ INSERT INTO viajes (PostgreSQL)
               → idViaje generado

Respuesta HTTP 201: TripResponseDTO completo
```

### 4.1 Reglas del TripPlannerOrchestrator

| Probabilidad RF | Nivel de alerta | Factor de tiempo | Acción adicional |
|---|---|---|---|
| < 40% | VERDE | × 1.00 | — |
| 40% – 70% | AMARILLO | × 1.20 | — |
| > 70% | ROJO | × 1.35 | Sugerir ruta alterna si distancia > 5 km |

**Ejemplo:** ruta base de 44 min, probabilidad RF = 75 % → tiempo ajustado = `⌈44 × 1.35⌉ = 60 min`. Alerta ROJO.

### 4.2 Restricciones de vehículo

El campo `idVehiculo` del `TripRequestDTO` permite al backend aplicar restricciones específicas por tipo de vehículo. Las motocicletas tienen prohibición de circulación en túneles (implementado en Sprint 5).

---

## 5. Esquema de base de datos

### 5.1 Tablas de referencia (datos de seed)

| Tabla | Descripción | Registros seed |
|---|---|---|
| `municipios` | 10 municipios del Valle de Aburrá | 10 |
| `comunas` | Comunas y corregimientos | 21 |
| `barrios` | Barrios por comuna | 46 |
| `tipos_vehiculo` | Catálogo de tipos de vehículo | 11 |
| `tipos_motor` | Catálogo de tipos de motor | 7 |

### 5.2 Tablas de negocio

**`usuarios`**

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | serial PK | Identificador |
| `nombre` | varchar | Nombre completo |
| `email` | varchar (UNIQUE) | Correo electrónico |
| `password_hash` | varchar | Hash bcrypt |
| `created_at` | timestamptz | Fecha de registro |

**`vehiculos`**

| Columna | Tipo | Descripción |
|---|---|---|
| `placa` | varchar(10) PK | Placa colombiana validada (value object `Placa.java`) |
| `id_usuario` | integer FK | Propietario |
| `id_tipo_vehiculo` | integer FK | Tipo de vehículo |
| `id_tipo_motor` | integer FK | Tipo de motor |

**`viajes`**

| Columna | Tipo | Nullable | Descripción |
|---|---|---|---|
| `id_viaje` | integer PK | NO | Autoincremental |
| `id_usuario` | integer FK | NO | Usuario que planificó |
| `id_vehiculo` | varchar(10) FK | SÍ | Vehículo usado (null si sin vehículo) |
| `lat_origen` | double precision | SÍ | Latitud del origen |
| `lng_origen` | double precision | SÍ | Longitud del origen |
| `lat_destino` | double precision | SÍ | Latitud del destino |
| `lng_destino` | double precision | SÍ | Longitud del destino |
| `nombre_origen` | varchar(255) | SÍ | Nombre legible del origen |
| `nombre_destino` | varchar(255) | SÍ | Nombre legible del destino |
| `distancia_metros` | integer | SÍ | Distancia de la ruta |
| `tiempo_estimado_min` | smallint | NO | Tiempo ajustado por lluvia |
| `hora_inicio` | timestamptz | NO | Momento de planificación |
| `hora_fin` | timestamptz | SÍ | Null hasta finalizar |
| `precipitacion_mm` | smallint | SÍ | 2, 5 o 10 mm según probabilidad |
| `finalizado` | boolean | NO | false por defecto |
| `user_rating` | smallint | SÍ | Calificación del usuario (no implementada) |

### 5.3 Historial de migraciones Flyway

| Versión | Archivo | Descripción |
|---|---|---|
| V1 | baseline (`init-docker.sql`) | Estado base: todas las tablas + datos seed |
| V2 | `V2__viajes_lat_lng.sql` | Agrega columnas de coordenadas, nombres y distancia a `viajes` |

---

## 6. Modelos de Machine Learning

### 6.1 Variables de entrada

| Variable | Unidad | Fuente |
|---|---|---|
| `temperatura_c` | °C | Google Weather API |
| `humedad_relativa_pct` | % | Google Weather API |
| `cobertura_nubosa_pct` | % | Inferida desde tipo de condición Google Weather (`CLEAR`→0%, `THUNDERSTORM`→100%) |
| `velocidad_viento_ms` | m/s | Google Weather API |
| `hora` | 0–23 | Timestamp del sistema |
| `mes` | 1–12 | Timestamp del sistema |

### 6.2 Modelos entrenados

| Modelo | Archivo | AUC | F1 | Descripción |
|---|---|---|---|---|
| Random Forest | `models/random_forest.pkl` | 0.82 | ~0.78 | Modelo principal para decisiones de alerta |
| Regresión Logística | `models/regresion_logistica.pkl` | — | 0.78 | Modelo de referencia / benchmark |

- Datos de entrenamiento: SIATA + Open-Meteo (Valle de Aburrá).
- Versión de scikit-learn fijada en 1.4.2 (debe coincidir entre entrenamiento y servicio).
- Resultado: clasificación binaria `llueve` / `no llueve` con probabilidad continua.

### 6.3 Endpoint de predicción ML

```
POST http://ml-service:8081/predecir/ambos

Request:
{
  "temperatura_c": 18.5,
  "humedad_relativa_pct": 82.0,
  "cobertura_nubosa_pct": 75.0,
  "velocidad_viento_ms": 2.3,
  "hora": 14,
  "mes": 4
}

Response:
[
  { "modelo": "random_forest",        "llueve": true, "probabilidad_lluvia": 0.7231, "etiqueta": "llueve" },
  { "modelo": "regresion_logistica",  "llueve": true, "probabilidad_lluvia": 0.6812, "etiqueta": "llueve" }
]
```

---

## 7. Seguridad

### 7.1 Autenticación JWT

- **Registro:** `POST /api/auth/register` → crea usuario con hash bcrypt, devuelve JWT.
- **Login:** `POST /api/auth/login` → valida credenciales, devuelve JWT.
- **Protección:** `JwtAuthenticationFilter` intercepta todas las rutas excepto `/api/auth/**`, `/actuator/health` y Swagger en perfil `dev`.
- **Perfil `dev`:** Spring Security configurado con `.permitAll()` para facilitar el desarrollo y las pruebas.
- **Perfil `prod`:** todas las rutas excepto health y Swagger requieren token válido en header `Authorization: Bearer <token>`.

### 7.2 Value Object `Placa`

La placa de vehículo es un value object inmutable (`ti.mdva.model.valueobjects.Placa`) que valida el formato colombiano mediante regex. No puede existir una placa inválida en el sistema.

---

## 8. APIs externas e integración

| Servicio | URL base | Uso |
|---|---|---|
| Google Directions API | `maps.googleapis.com/maps/api/directions/json` | Ruta óptima, duración, distancia, polyline, pasos |
| Google Geocoding API | `maps.googleapis.com/maps/api/geocode/json` | Resolución de `placeId` a coordenadas |
| Google Weather API | `weather.googleapis.com/v1/currentConditions:lookup` | Condiciones actuales por coordenada |
| Google Weather API (grid) | `weather.googleapis.com/v1/...` | Datos de cuadrícula para mapa de calor |
| Google Maps JS API | `maps.googleapis.com` (JS SDK) | Mapa interactivo, polyline, 3D en frontend |
| FastAPI ML | `http://ml-service:8081` | Predicción de lluvia (interno Docker) |
| FastAPI Routing | `http://routing-service:8000` | Enrutamiento ambiental (interno Docker) |

### 8.1 Configuración de credenciales

| Capa | Ubicación de la key |
|---|---|
| Backend en Docker | Variable de entorno `GOOGLE_MAPS_API_KEY` en `docker-compose.dev.yml` |
| Backend local | `Backend/src/main/resources/application-dev.yml` → `google.maps.api-key` |
| Frontend en Docker | `Frontend/.env.production` → `VITE_GOOGLE_MAPS_KEY` |
| Frontend local | `Frontend/.env` → `VITE_GOOGLE_MAPS_KEY` |

> **Nota de seguridad:** La key actual es de desarrollo y está vinculada a la cuenta de Google de Camilo Ardila. Para producción debe rotarse y restringirse por dominio/IP.

---

## 9. Infraestructura y contenedores

### 9.1 Servicios Docker Compose

| Servicio | Imagen / Dockerfile | Puerto host | Puerto interno | Contenedor |
|---|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | 5436 | 5432 | `mdva-postgres` |
| ML Service | `./Data-science/Dockerfile` | 8081 | 8081 | `mdva-ml` |
| Routing Service | `./Data-science/enrutamiento_ambiental/Dockerfile` | 8000 | 8000 | `mdva-routing` |
| Backend | `./Backend/Dockerfile` | 8080 | 8080 | `mdva-backend` |
| Frontend | `./Frontend/Dockerfile` | 8090 | 80 | `mdva-frontend` |

### 9.2 Volúmenes persistentes

| Volumen | Montado en | Propósito |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Datos de la BD entre reinicios |
| `routing_graph_cache` | `/app/cache` | Grafo OSM + modelo Rain descargados |

### 9.3 Build del Backend

El `Dockerfile` del backend usa un build multietapa:
1. **Etapa compile:** JDK Alpine + Gradle → compila el JAR.
2. **Etapa runtime:** JRE Alpine → ejecuta el JAR.

El script `gradlew` tiene CRLF (editado en Windows); el `Dockerfile` aplica `sed -i 's/\r$//'` antes de ejecutarlo.

### 9.4 CI/CD

Configurado parcialmente con GitHub Actions (`./github/workflows/release.yml`). Los workflows identifican todos los pushes pero la integración completa está pendiente (HU025).

---

## 10. Supuestos técnicos

| Supuesto | Detalle |
|---|---|
| Disponibilidad de Google APIs | La cuota gratuita de Google Cloud Platform es suficiente para el volumen de pruebas del prototipo |
| scikit-learn 1.4.2 | La versión fijada en `requirements.txt` debe coincidir con la versión con la que fueron entrenados los modelos `.pkl` |
| Puerto 5436 para PostgreSQL | El mapeo no estándar `5436→5432` evita conflicto con instancias locales de PostgreSQL en máquinas de desarrollo |
| Cobertura nubosa inferida | El endpoint `currentConditions` de Google Weather no expone cobertura nubosa directamente; se infiere desde el tipo de condición. Para cobertura exacta se requeriría `forecast/hours` |
| Red interna Docker | La comunicación entre `backend`, `ml-service` y `routing-service` usa los nombres de contenedor Docker como hostnames (`http://ml-service:8081`) |
| Grafo OSM | El primer arranque del `routing-service` descarga el grafo del Valle de Aburrá desde OpenStreetMap; puede tardar varios minutos. El grafo queda cacheado en el volumen `routing_graph_cache` |
| Usuario final | Dispositivo con navegador moderno (Chrome 90+) y conexión a internet móvil |

---

## 11. Decisiones técnicas relevantes

**Google Weather API en lugar de Open-Meteo:** Open-Meteo presentaba double-encoding del timezone (`America%252FBogota`). Google Weather API usa la misma key ya activa y devuelve probabilidad de lluvia directamente.

**JOOQ DAOs fuera del component scan:** Los DAOs generados viven en `ti.mdva.jooq.tables.daos`, fuera del paquete base. `JooqDaoConfig` en `ti.mdva.config` los registra manualmente como beans de Spring.

**`TripPlannerOrchestrator` sin estado:** Clase estática sin dependencias inyectadas, lo que facilita las pruebas unitarias aisladas.

**`Placa` como value object:** Reemplazó al anterior `ValidadorPlacasService`. Al ser inmutable, no puede existir una placa inválida en el dominio.

**Lombok no usado en clases nuevas del Sprint 3+:** Incompatibilidad del indexador NetBeans/LSP con la versión de Lombok. Los DTOs existentes sí usan `@Data`/`@Builder` y compilan correctamente con Gradle.

**`init-docker.sql` refleja estado post-V2:** Para que Flyway no falle en contenedores nuevos al intentar `ALTER TABLE` sobre columnas ya existentes, las migraciones usan `IF NOT EXISTS` y el script base ya incluye las columnas de V2.

---

*MDVA — Informe Técnico · Sprint 5 · Mayo 2026*
