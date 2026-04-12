# MDVA — Monitoreo de Variables Ambientales
## Documentación de avances Sprint 3 - Camilo

**Estado:** Lógica de viajes implementada a partir de coordenadas GPS, consumo de API con modelos de ML para recomendaciones 
**Rama en con el estado actual:** `feature/ViajesDeployment`  

## 1. Arquitectura general

El sistema está compuesto por cuatro servicios independientes orquestados con Docker Compose. Cada servicio corre en su propio contenedor y se comunica a través de la red interna de Docker.

| Servicio | Tecnología | Puerto host | Puerto interno | Contenedor |
|---|---|---|---|---|
| PostgreSQL 16 | `postgres:16-alpine` | **5436** | 5432 | `mdva-postgres` |
| ML Service | FastAPI · Python 3.11 | **8081** | 8081 | `mdva-ml` |
| Backend | Spring Boot 3.4.2 · Java 21 | **8080** | 8080 | `mdva-backend` |
| Frontend | React + Vite · nginx | **8090** | 80 | `mdva-frontend` |

> **Nota sobre el puerto de PostgreSQL:** el mapeo es `5436→5432` (en lugar del estándar) porque la máquina de desarrollo de Camilo tiene instancias locales de PostgreSQL 18 ocupando varios puertos.

### 1.1 Flujo de datos — `POST /api/viajes/planificar`

Cuando el usuario solicita planificar un viaje, el backend orquesta tres llamadas externas en secuencia:

```
Cliente
  └─► ViajeController
        └─► ViajeUseCase
              ├─► GoogleMapsService.resolveCoordinates()   → Geocoding API (si viene placeId)
              ├─► GoogleMapsService.getOptimalRoute()      → Directions API
              ├─► WeatherMLService.predictRainForLocation()
              │     ├─► Google Weather API (currentConditions:lookup)
              │     └─► FastAPI /predecir/ambos
              ├─► TripPlannerOrchestrator.apply()          → Ajuste de tiempo + alerta
              └─► ViajeRepository.save()                   → PostgreSQL
```

Paso a paso:

1. El `ViajeController` recibe el `TripRequestDTO` con coordenadas de origen y destino.
2. `GoogleMapsService.resolveCoordinates()` valida y enriquece los puntos (soporta `placeId` de Google Places o coordenadas directas lat/lng).
3. `GoogleMapsService.getOptimalRoute()` consulta la Directions API y retorna duración en segundos, distancia en metros, polyline codificada y pasos de navegación.
4. `WeatherMLService.predictRainForLocation()` hace dos llamadas en cadena:
   - **GET** `weather.googleapis.com/v1/currentConditions:lookup` — obtiene temperatura, humedad, viento y probabilidad de lluvia.
   - **POST** `FastAPI /predecir/ambos` — envía las variables climáticas y obtiene predicciones de ambos modelos ML.
5. `TripPlannerOrchestrator.apply()` combina la ruta y la predicción para calcular el tiempo ajustado y el nivel de alerta.
6. `ViajeRepository.save()` persiste el viaje en PostgreSQL con todos los campos.
7. El controller retorna **HTTP 201** con el `TripResponseDTO` completo, incluyendo el ID generado por la BD.

---

## 2. Stack tecnológico

### 2.1 Backend — Spring Boot

| Componente | Detalle |
|---|---|
| Framework | Spring Boot 3.4.2 sobre Java 21 (Eclipse Temurin JDK Alpine en Docker) |
| ORM / Queries | JOOQ 3.19.18 con generación de código desde PostgreSQL. DAOs registrados como beans vía `JooqDaoConfig` en `ti.mdva.config` |
| Migraciones BD | Flyway con `baseline-on-migrate=true`. V1 es el estado base (`init-docker.sql`). V2 agrega las columnas de coordenadas a `viajes` |
| Seguridad | Spring Security: perfil `dev` permite todos los endpoints sin autenticación. Perfil `prod` protege todos excepto `/actuator/health` y Swagger |
| Build | Gradle 9.2 con Kotlin DSL. Lombok para DTOs. `generateJooq` conecta a `localhost:5436` |
| Documentación API | Swagger UI en `http://localhost:8080/swagger-ui.html` |

### 2.2 Microservicio ML — FastAPI

Servicio Python independiente que carga dos modelos scikit-learn al arrancar. Si un modelo no está disponible en disco, el servicio arranca con los que encuentre (tolerante a modelos faltantes) y devuelve HTTP 503 si se solicita un modelo no cargado. **(Recordar que uno de los dos modelos no está en el repositorio debido a su gran tamaño, ver .gitignore para el resto de archivos que se requieren)**

| Modelo | AUC | Archivo |
|---|---|---|
| Random Forest | **0.82** | `Data-science/models/random_forest.pkl` |
| Regresión Logística | 0.78 | `Data-science/models/regresion_logistica.pkl` |

El endpoint `/predecir/ambos` recibe:

```json
{
  "temperatura_c": 18.5,
  "humedad_relativa_pct": 82.0,
  "cobertura_nubosa_pct": 75.0,
  "velocidad_viento_ms": 2.3,
  "hora": 14,
  "mes": 4
}
```

> Para el campo de la cobertura nubosa se infiere desde el tipo de condición de Google Weather API (ej. `CLEAR` → 0%, `THUNDERSTORM` → 100%) porque el endpoint `currentConditions` no la expone directamente. Para cobertura exacta habría que usar `forecast/hours`.

### 2.3 Base de datos — PostgreSQL 16

La BD se inicializa con `DB/init-docker.sql` en el primer arranque del contenedor. Este script refleja el estado post-V2 y crea todas las tablas ya con las columnas de coordenadas incluidas. Flyway luego aplica las migraciones incrementales.

**Tablas de referencia preexistentes (datos de seed):**
- `municipios`, `comunas`, `barrios` — geografía del Valle de Aburrá (10 municipios, 21 comunas, 46 barrios)
- `tipos_vehiculo`, `tipos_motor` — catálogos (11 tipos de vehículo, 7 tipos de motor)
- `usuarios` — 1 usuario de desarrollo (`id=1`)
- `vehiculos` — flota de vehículos por usuario con placa colombiana validada

### 2.4 Frontend — React

Vite + React, despliegue por nginx dentro del contenedor.

**Recordar que este es un frontend que se desarrolló para probar el funcionamiento de los componentes en simultáneo, está pendiente enlazar con el manejo de autenticación desarrollado por Santiago**

| Ruta | Descripción |
|---|---|
| `/` | Formulario para planificar un viaje. Incluye botones de llenado rápido para rutas de prueba |
| `/viaje/:id` | Resultado: estadísticas, mapa con polyline, predicción climática y botón finalizar |
| `/historial/:userId` | Lista de todos los viajes del usuario con estado y metadatos |

**Dependencias clave:**
- `axios` — llamadas al backend
- `@vis.gl/react-google-maps` — mapa y decodificación de polyline
- `react-router-dom` — navegación SPA

---

## 3. APIs externas y credenciales

**Todas las APIs de Google usan la misma key de desarrollo, la cual, está enlazada a la cuenta de Google de Camilo. Para producción se debe rotar por una key con restricciones por dominio/IP.**

| Servicio | URL base | Notas |
|---|---|---|
| Google Directions API | `maps.googleapis.com/maps/api/directions/json` | Ruta óptima, duración, distancia, polyline |
| Google Geocoding API | `maps.googleapis.com/maps/api/geocode/json` | Resuelve `placeId` a coordenadas |
| Google Weather API | `weather.googleapis.com/v1/currentConditions:lookup` | Reemplazó Open-Meteo. En Preview: sin costo |
| Google Maps JavaScript API | `maps.googleapis.com` (JS) | Mapa y decodificación de polyline en el frontend |
| FastAPI ML (interno) | `http://ml-service:8081` (Docker) | Sin autenticación en dev |

### Credenciales de desarrollo (Analizar si se deben configurar github secrets o un .env en producción)


```
Se decide subir el docker compose sin .env al repositorio debido a que este está privado y las credenciales son de testing
**También se sube la API KEY de google en el docker compose, posiblemente ssea mejor definir credenciales en github secrets y un .env en el servidor una vez estemos desplegando**
```

### Dónde está configurada la key

| Capa | Ubicación |
|---|---|
| Backend en Docker | Variable de entorno `GOOGLE_MAPS_API_KEY` en `docker-compose.dev.yml` |
| Backend local | `Backend/src/main/resources/application-dev.yml` → `google.maps.api-key` |
| Frontend en Docker | `Frontend/.env.production` → `VITE_GOOGLE_MAPS_KEY` |
| Frontend dev local | `Frontend/.env` → `VITE_GOOGLE_MAPS_KEY` |

### Credenciales de PostgreSQL (desarrollo)

```
Host:     localhost
Puerto:   5436
BD:       mdva
Usuario:  postgres
Password: cambiame-db-password
```

---

## 4. Esquema de la tabla `viajes`

Esta tabla es el núcleo del sistema. Registra cada viaje planificado con toda la información de ruta, clima y predicción ML.

| Columna | Tipo | Nullable | Descripción |
|---|---|---|---|
| `id_viaje` | `integer` | NO | PK, autoincremental |
| `id_usuario` | `integer` | NO | FK a `usuarios.id` |
| `id_vehiculo` | `varchar(10)` | SÍ | FK a `vehiculos.placa`. Nulo si no registró vehículo |
| `id_barrio_origen` | `varchar(255)` | SÍ | **Legado V1.** A eliminar en V3 |
| `id_barrio_destino` | `varchar(255)` | SÍ | **Legado V1.** A eliminar en V3 |
| `lat_origen` ⭐ | `double precision` | SÍ | Latitud del origen. **Agregado en V2** |
| `lng_origen` ⭐ | `double precision` | SÍ | Longitud del origen. **Agregado en V2** |
| `lat_destino` ⭐ | `double precision` | SÍ | Latitud del destino. **Agregado en V2** |
| `lng_destino` ⭐ | `double precision` | SÍ | Longitud del destino. **Agregado en V2** |
| `nombre_origen` ⭐ | `varchar(255)` | SÍ | Nombre legible del origen (ej: "Medellín Centro"). **Agregado en V2** |
| `nombre_destino` ⭐ | `varchar(255)` | SÍ | Nombre legible del destino. **Agregado en V2** |
| `distancia_metros` ⭐ | `integer` | SÍ | Distancia de la ruta en metros. **Agregado en V2** |
| `tiempo_estimado_min` | `smallint` | NO | Tiempo ajustado por lluvia |
| `hora_inicio` | `timestamptz` | NO | Momento de planificación |
| `hora_fin` | `timestamptz` | SÍ | Nulo hasta llamar `PATCH /finalizar` |
| `precipitacion_mm` | `smallint` | SÍ | Precipitación estimada: 2, 5 o 10 mm según probabilidad |
| `finalizado` | `boolean` | NO | `false` por defecto |
| `user_rating` | `smallint` | SÍ | Calificación del usuario. No implementada aún |

> ⭐ Columnas agregadas en la migración `V2__viajes_lat_lng.sql`. El índice `idx_viajes_usuario_hora` optimiza las consultas de historial por usuario ordenadas por fecha.

### Historial de migraciones Flyway, se corren automáticamente sobre el esquema base

| Versión | Archivo | Descripción |
|---|---|---|
| V1 | baseline | Estado base creado por `init-docker.sql` |
| V2 | `V2__viajes_lat_lng.sql` | Agrega columnas lat/lng, nombres y distancia a `viajes` |

---

## 5. Lógica de planificación y ajuste por lluvia

### 5.1 Reglas de ajuste — `TripPlannerOrchestrator`

El `TripPlannerOrchestrator` usa la probabilidad del modelo **Random Forest** (AUC 0.82) como referencia:

| Probabilidad RF | Nivel alerta | Factor tiempo | Acción adicional |
|---|---|---|---|
| < 40% | 🟢 VERDE | × 1.00 | Ninguna |
| 40% – 70% | 🟡 AMARILLO | × 1.20 | Ninguna |
| > 70% | 🔴 ROJO | × 1.35 | Sugerir ruta alterna si distancia > 5 km |

**Ejemplo:** ruta base de 44 min con probabilidad 75% → `ceil(44 × 1.35) = 60 min`. Alerta ROJO. Si la ruta supera 5 km, se incluye `razonRutaAlterna` en la respuesta.

### 5.2 Campos del `TripResponseDTO`

```
idViaje               → ID generado por la BD
horaInicio            → timestamp de planificación
origen / destino      → { lat, lng, displayName, placeId }
tiempoBaseMin         → tiempo sin ajuste (Google Directions)
tiempoEstimadoMin     → tiempo ajustado por lluvia
factorAjuste          → 1.00 | 1.20 | 1.35
distanciaMetros       → distancia de la ruta
overviewPolyline      → polyline codificada (decodificar con google.maps.geometry.encoding.decodePath())
pasos                 → lista de RouteStepDTO con instrucciones de navegación
prediccionLluvia      → { probabilidadRf, probabilidadRl, llueve, temperaturaC,
                          humedadPct, coberturaAnubosaPct, velocidadVientoMs }
alertaNivel           → VERDE | AMARILLO | ROJO
alertaMensaje         → texto explicativo del riesgo
sugerirRutaAlterna    → boolean
razonRutaAlterna      → texto explicativo si aplica
```

---

## 6. Cómo ejecutar el sistema

### 6.1 Prerrequisitos

- Docker Desktop instalado y corriendo
- Node.js 24+ y npm 11+ (solo para desarrollo local del frontend)

### 6.2 Levantar el stack completo

Desde la raíz del repositorio y en la rama `feature/ViajesDeployment` :

```bash
docker compose -f docker-compose.dev.yml up --build
```

Los servicios arrancan en orden por dependencias:
```
Postgres (healthcheck: pg_isready)
  → ML Service (healthcheck: GET /health)
    → Backend (Spring Boot)
      → Frontend (nginx)
```

El primer arranque tarda varios minutos porque descarga las imágenes base y compila el JAR de Spring Boot dentro del contenedor.


### 6.3 Verificar que todo funciona

| Verificación | URL / comando |
|---|---|
| Frontend | http://localhost:8090 |
| Backend health | http://localhost:8080/actuator/health |
| Swagger UI | http://localhost:8080/swagger-ui.html |
| ML health | http://localhost:8081/health |
| ML docs | http://localhost:8081/docs |
| PostgreSQL | `psql -h localhost -p 5436 -U postgres -d mdva` |

### 6.4 Regenerar JOOQ tras cambios de esquema

Con los contenedores corriendo (PostgreSQL en el puerto 5436), desde la carpeta `Backend/`:

```bash
./gradlew generateJooq
```

> El `build.gradle.kts` apunta a `jdbc:postgresql://localhost:5436/mdva`. El `generateJooq` debe correr con los contenedores activos — si hay un PostgreSQL local también en el host, verificar que no esté en el mismo puerto antes de regenerar.

Tras regenerar, reconstruir el backend:

```bash
docker compose -f docker-compose.dev.yml up --build backend
```

**Comentarle a Camilo cualquier error en la ejecución para ver cómo resolverlo y que funcione en todas las máquinas**

---

## 7. Estructura del repositorio

```
Monitoreo-de-variables-ambientales/
│
├── docker-compose.dev.yml          ← Orquestación de los 4 servicios
│
├── Backend/
│   ├── Dockerfile                  ← Build multietapa: JDK Alpine (compile) + JRE Alpine (runtime)
│   ├── build.gradle.kts            ← Gradle Kotlin DSL. JOOQ apunta a localhost:5436
│   ├── src/main/java/ti/mdva/
│   │   ├── config/
│   │   │   ├── JooqDaoConfig.java  ← Registra los DAOs de JOOQ como beans de Spring
│   │   │   ├── SecurityConfig.java ← Perfiles dev (abierto) y prod (protegido)
│   │   │   └── CorsConfig.java
│   │   ├── controller/             ← ViajeController, WeatherController, LocationController
│   │   ├── usecases/               ← ViajeUseCase (orquesta el flujo completo)
│   │   ├── service/
│   │   │   ├── impl/
│   │   │   │   ├── GoogleMapsServiceImpl.java   ← Directions + Geocoding API
│   │   │   │   └── WeatherMLServiceImpl.java    ← Google Weather API → FastAPI ML
│   │   │   └── TripPlannerOrchestrator.java     ← Reglas de ajuste por lluvia
│   │   ├── repositories/           ← ViajeRepositoryImpl, VehiculoRepositoryImpl
│   │   ├── model/
│   │   │   ├── dto/                ← TripRequestDTO, TripResponseDTO, RainPredictionDTO, etc.
│   │   │   └── valueobjects/
│   │   │       └── Placa.java      ← Value object inmutable con regex para placas colombianas
│   │   └── exception/
│   │       └── GlobalExceptionHandler.java
│   ├── src/main/resources/
│   │   ├── application.yml         ← Configuración base (perfil-agnostic)
│   │   ├── application-dev.yml     ← Credenciales de desarrollo (NO commitear en prod)
│   │   └── db/migration/
│   │       └── V2__viajes_lat_lng.sql
│   └── src/main/generated-jooq/    ← Código JOOQ generado (NO editar manualmente)
│
├── Data-science/
│   ├── Dockerfile                  ← Python 3.11-slim. scikit-learn fijado en 1.4.2
│   ├── main.py                     ← Entrypoint FastAPI. Tolerante a modelos faltantes
│   ├── requirements.txt            ← scikit-learn==1.4.2 (debe coincidir con versión de entrenamiento)
│   ├── models/
│   │   ├── random_forest.pkl
│   │   └── regresion_logistica.pkl
│   └── notebooks/                  ← Notebooks de entrenamiento
│
├── DB/
│   ├── init-docker.sql             ← Script de inicialización del contenedor (estado post-V2)
│   ├── TIC1DB.sql                  ← Respaldo SQL
│   └── TIC1DB.backup               ← Respaldo binario
│
└── Frontend/
    ├── Dockerfile                  ← Build con Node 24 Alpine → serve con nginx
    ├── nginx.conf                  ← SPA fallback: todas las rutas → index.html
    ├── .env                        ← Variables para desarrollo local (npm run dev)
    ├── .env.production             ← Variables para build de Docker
    └── src/
        ├── api/
        │   └── client.js           ← Todas las llamadas al backend centralizadas con axios
        ├── components/
        │   ├── MapaRuta.jsx        ← Mapa con polyline decodificada
        │   ├── AlertaClimatica.jsx ← Predicción ML + nivel de alerta
        │   └── TarjetaViaje.jsx    ← Card para historial
        └── pages/
            ├── PlanificarViaje.jsx
            ├── ResultadoViaje.jsx
            └── HistorialViajes.jsx
```

---

## 8. Decisiones técnicas y cambios relevantes

**`Placa` como Value Object:** `ValidadorPlacasService` fue eliminado y reemplazado por `Placa.java` en `ti.mdva.model.valueobjects`. Inmutable — no puede existir una placa inválida en el sistema.

**`TripPlannerOrchestrator` como clase utilitaria estática:** Sin estado ni dependencias inyectadas. Encapsula solo las reglas de negocio de ajuste, lo que facilita el testing unitario independiente.

**Google Weather API en lugar de Open-Meteo:** Open-Meteo fallaba con doble-encoding del timezone (`America%252FBogota` en lugar de `America%2FBogota`). Google Weather API usa la misma key que Directions/Geocoding ya activa en el proyecto y además retorna probabilidad de lluvia directamente como dato de respaldo.

**`JooqDaoConfig` en `ti.mdva.config` (no en `ti.mdva.jooq`):** Los DAOs generados por JOOQ viven en `ti.mdva.jooq.tables.daos`, fuera del component scan de `@SpringBootApplication`. La config que los registra como beans debe estar en `ti.mdva.*` para ser encontrada por Spring.

**Lombok no usado en clases nuevas del Sprint 3:** `GoogleMapsServiceImpl`, `WeatherMLServiceImpl` y otras clases nuevas usan logger manual y constructor explícito porque el indexador de NetBeans (LSP) tiene incompatibilidad con la versión de Lombok instalada. Los DTOs sí usan `@Data`/`@Builder` y compilan correctamente con Gradle (el error es solo en el IDE).

**Puerto PostgreSQL 5436:** Se cambió de 5432 porque la máquina de desarrollo tiene PostgreSQL 18 instalado localmente ocupando 5432, 5433 y 5434. El `build.gradle.kts` para `generateJooq` apunta a `localhost:5436`.

**`init-docker.sql` refleja estado post-V2:** El script de inicialización crea la tabla `viajes` ya con las columnas `lat_*`/`lng_*` para que Flyway no falle al intentar `ALTER TABLE` sobre columnas que ya existen en un contenedor nuevo. Flyway registra V2 como aplicada aunque las columnas ya estén (usa `IF NOT EXISTS`).

**`scikit-learn` fijado en 1.4.2:** Los modelos `.pkl` fueron entrenados con esta versión. Usar una versión diferente en el contenedor generaba `InconsistentVersionWarning` que podría derivar en resultados incorrectos. `requirements.txt` fija `scikit-learn==1.4.2`.

**Dockerfile backend usa `sed -i 's/\r$//' gradlew`:** El archivo `gradlew` tiene line endings CRLF (fue editado en Windows). Alpine Linux no puede ejecutar scripts con `\r` en el shebang. El `sed` limpia los CRLF antes de darle permisos de ejecución.

---

## 9. Pendientes (TODO de Camilo) y próximos pasos

### Corto plazo

- **Migración V3:** eliminar columnas `id_barrio_origen` e `id_barrio_destino` de la tabla `viajes` (mantenidas por compatibilidad histórica desde V1).
- **`user_rating`:** implementar el flujo de calificación en el endpoint de finalización de viaje.
- **Integración con la autenticación real de Santiago:** JWT o OAuth2 en Spring Security para perfil `prod`.
- **Revisar Random Forest, el cual, fue ajustado:** exportar el `.pkl` con scikit-learn 1.4.2 con datos más recientes del Valle de Aburrá.

### Mediano plazo

- **Google Places Autocomplete:** integrar en el formulario del frontend en lugar de ingreso manual de coordenadas.
- **Turn-by-turn:** mostrar los pasos de navegación en la vista de resultado del viaje.
- **Caché de predicciones climáticas:** evitar llamadas redundantes a Google Weather API para viajes simultáneos al mismo origen (Definir una ventana de tiempo para no gastar muchos créditos).
- **CI/CD:** configurar mejor los workflows debido a que actualmente todos los pushes son identificados como fallidos a nivel de workflow.

---

## 10. Referencia de endpoints

### Backend — `http://localhost:8080`

| Método | Ruta | HTTP | Descripción |
|---|---|---|---|
| POST | `/api/viajes/planificar` | 201 | Planifica un viaje completo. Body: `TripRequestDTO`. Retorna `TripResponseDTO` con ruta, ML y alerta |
| PATCH | `/api/viajes/{id}/finalizar` | 200 | Marca el viaje como finalizado, registra `hora_fin` |
| GET | `/api/viajes/{id}` | 200/404 | Obtiene un viaje por ID |
| GET | `/api/viajes/usuario/{idUsuario}` | 200 | Historial completo de viajes de un usuario |
| GET | `/api/locations/municipalities` | 200 | Lista de municipios del Valle de Aburrá |
| GET | `/api/locations/municipalities/{id}/communes` | 200 | Comunas de un municipio |
| GET | `/api/locations/communes/{id}/neighborhoods` | 200 | Barrios de una comuna |
| GET/POST | `/api/weather/current` | 200 | Condiciones climáticas actuales (Open-Meteo, independiente del flujo ML) |
| GET | `/actuator/health` | 200 | Health check del backend |
| GET | `/swagger-ui.html` | — | Documentación interactiva de toda la API |

### Ejemplo de request — planificar viaje

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

### Microservicio ML — `http://localhost:8081`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check. Muestra modelos cargados |
| GET | `/docs` | Documentación Swagger del microservicio ML |
| POST | `/predecir/ambos` | Predicción con ambos modelos en paralelo |
| POST | `/predecir/random_forest` | Predicción solo con Random Forest |
| POST | `/predecir/regresion_logistica` | Predicción solo con Regresión Logística |

### Ejemplo de request — predicción ML directa

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

*MDVA — Monitoreo de Variables Ambientales · Documentación generada Sprint 3 · Abril 2026*
