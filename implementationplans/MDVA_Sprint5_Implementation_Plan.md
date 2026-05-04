# MDVA — Plan de Implementación Sprint 5
**Monitoreo de Variables Ambientales · Abril 2026**

---

## Estado actual del proyecto

### Lo que hicieron tus compañeros

| Autor | Commit | Alcance |
|---|---|---|
| **Santiago A. Martínez** | `feat: integración ML, JWT auth, Flyway migrations, Docker` | Trabajo más pesado del equipo. Implementó: esquema Flyway V1/V2/V3, JWT completo con BCrypt (JwtUtil, JwtAuthenticationFilter, SecurityConfig), endpoints /auth/register y /auth/login, integración backend con FastAPI ML via PredictionServiceImpl y EnvironmentServiceImpl, Docker Compose funcional con postgres + backend + ml-service, CORS config. |
| **Nicolás Meneses** | `Última presentación: REVISAR` | Implementó la pantalla EnRuta.jsx — base de la navegación GPS en vivo: polyline de la ruta sobre Google Maps, marcador del conductor que se mueve con watchPosition, panel inferior con estado del viaje y botón de finalizar. También implementó PlanificarViaje.jsx con Google Places Autocomplete. |
| **Nicolás Meneses** | `Arreglo de falla CI/CD` | Creó V1__initial_schema.sql idempotente para que Flyway arranque en contenedores limpios y corrigió application.yml. |

### Estado actual de la arquitectura

```
Frontend (React + Vite) puerto 8090
  - /login, /register
  - /              MapaCiudad.jsx (mapa estático)
  - /planificar    PlanificarViaje.jsx (Google Places Autocomplete OK)
  - /viaje/:id     ResultadoViaje.jsx (stats + mapa + predicción)
  - /viaje/:id/en-ruta  EnRuta.jsx (GPS en vivo básico OK)

Backend (Spring Boot) puerto 8080
  - POST /auth/register, /auth/login (JWT OK)
  - POST /api/viajes/planificar (Google Directions + ML OK)
  - PATCH /api/viajes/{id}/finalizar
  - GET  /api/viajes/{id}
  - GET  /api/viajes/usuario/{id}

ML Service (FastAPI) puerto 8081
  - POST /predecir/ambos (RF + RL OK)
  - POST /predecir/{modelo}

DB (PostgreSQL 16)
  - V1: schema base (usuarios, vehículos, viajes, barrios)
  - V2: lat/lng en viajes
  - V3: drop barrio columns
```

### Qué NO existe todavía (target del Sprint 5)

- Navegación turn-by-turn (instrucciones paso a paso en tiempo real)
- Icono de navegación con heading (dirección) — solo círculo estático
- Recomendaciones climáticas activas durante el trayecto
- Capa de calor de lluvia sobre el mapa
- Soporte de múltiples paradas en un viaje
- Modo claro/oscuro + UI optimizada para sol directo

---

## Mapa de features a Sprints

| Feature | Sprint |
|---|---|
| UI Refactor: modo claro/oscuro, legibilidad | Sprint 5.0 (prerequisito visual) |
| Trayecto GPS en vivo — estilo Waze | Sprint 5.1 |
| Recomendaciones activas durante trayecto | Sprint 5.2 |
| Capa de calor climático en el mapa | Sprint 5.2 |
| Múltiples paradas en un viaje | Sprint 5.3 |

---

## Sprint 5.0 — Refactorización UI (Modo Claro/Oscuro)

### Objetivo
Preparar la base visual para que la app sea usable bajo cualquier condición de luz ambiental — en el carro, al sol, de noche — antes de implementar las features de navegación.

### Frontend

**index.css — Sistema de tokens dual**

Cambiar el sistema de colores a variables CSS que respondan a `data-theme`:

```css
[data-theme="dark"] {
  --bg:      #0a0c10;
  --surface: #111318;
  --text:    #e8eaf0;
  --muted:   #5a6070;
  --accent:  #4af0a0;
  --accent2: #f0a04a;
  --border:  #1e2330;
}

[data-theme="light"] {
  --bg:      #f5f7fa;
  --surface: #ffffff;
  --text:    #1a1d26;
  --muted:   #7a8090;
  --accent:  #0d9e65;
  --accent2: #c87a1f;
  --border:  #d8dde8;
}
```

**ThemeToggle.jsx** — Botón de toggle en el navbar (ícono sol/luna) que escribe `data-theme` en `<html>` y persiste en `localStorage`.

**EnRuta.jsx — Modo Conducción** — Panel inferior rediseñado con tipografía más grande, colores de alto contraste tipo HUD, siempre independientemente del tema global.

**App.jsx** — leer `localStorage.getItem('theme')` al iniciar y aplicar al elemento html.

### DB / Backend
Sin cambios — es puramente frontend.

### Criterios de aceptación
- Toggle visible en la navbar, persiste entre sesiones.
- Bajo luz directa (modo claro), todos los textos tienen contraste mayor o igual a 4.5:1 (WCAG AA).
- El panel de conducción (EnRuta) siempre usa paleta oscura con texto grande.

---

## Sprint 5.1 — Trayecto GPS en Vivo (Estilo Waze)

### Objetivo
Convertir EnRuta.jsx de un mapa con un punto que se mueve a una experiencia de navegación real: instrucciones paso a paso, icono con dirección, cámara que sigue al conductor, estimación de llegada dinámica.

### Frontend — EnRuta.jsx (modificaciones mayores)

**1. Icono de navegación con heading**
- Reemplazar el SymbolPath.CIRCLE estático por un SVG de flecha de navegación.
- Usar `coords.heading` de watchPosition para rotar el marcador según la dirección de movimiento.
- Fallback: mantener la última rotación conocida cuando heading es null.
- Animación suave de rotación con CSS transition.

**2. Snap-to-road y seguimiento de cámara**
- En cada actualización de posición: map.panTo(posicion) con zoom 17.
- Botón "Centrar" que aparece cuando el usuario mueve el mapa manualmente (detectado con evento center_changed).

**3. Instrucciones turn-by-turn**

Los steps de Google Directions ya vienen en TripResponseDTO. Hay que:
- Parsear los pasos en el frontend (coordenadas + instrucción HTML).
- Calcular qué paso es el actual comparando la posición GPS contra el start_location de cada paso (distancia Haversine).
- Mostrar la instrucción actual en un banner superior (fondo semitransparente, texto grande, ícono de maniobra).

**4. ETA dinámica**
- Calcular distancia restante desde posición actual hasta destino (Haversine local, sin llamada extra a la API).
- Mostrar ETA actualizado dinámicamente.

**Nuevo componente: NavigationHeader.jsx** — Banner superior superpuesto al mapa con instrucción actual, ETA y distancia restante.

**Nuevo componente: NavigationPanel.jsx** — Panel lateral colapsable con la lista completa de pasos del viaje.

### Backend
Verificar que TripResponseDTO.StepDTO expone htmlInstructions, startLocation.lat, startLocation.lng. Si falta algún campo, añadirlo al DTO — sin cambios de lógica, solo de mapeo.

Sin cambios de DB — los pasos son efímeros.

### ML Service
Sin cambios.

### Criterios de aceptación
- El icono de navegación rota según la dirección de movimiento.
- El mapa sigue automáticamente al conductor (pan-to en cada update GPS).
- La instrucción del paso actual se muestra prominentemente en el banner superior.
- La ETA se actualiza en tiempo real.
- El usuario puede ver todos los pasos en un panel lateral.

---

## Sprint 5.2 — Recomendaciones Activas + Capa de Calor Climático

### Objetivo
Mientras el conductor está en ruta: (a) evaluar periódicamente las condiciones climáticas y emitir recomendaciones accionables, (b) superponer capa visual de calor de lluvia sobre el mapa.

---

### Bloque A: Recomendaciones Activas

#### DB — Migración V4

**Tabla condiciones_snapshot**

```sql
CREATE TABLE condiciones_snapshot (
    id_viaje              INTEGER PRIMARY KEY REFERENCES viajes(id_viaje),
    probabilidad_rf       DOUBLE PRECISION,
    probabilidad_rl       DOUBLE PRECISION,
    temperatura_c         DOUBLE PRECISION,
    humedad_pct           DOUBLE PRECISION,
    cobertura_nubosa_pct  DOUBLE PRECISION,
    velocidad_viento_ms   DOUBLE PRECISION,
    alerta_nivel_inicio   VARCHAR(10),
    timestamp_snapshot    TIMESTAMPTZ,
    timestamp_dato_weather TIMESTAMPTZ
);
```

**Tabla alertas_viaje**

```sql
CREATE TABLE alertas_viaje (
    id_alerta              SERIAL PRIMARY KEY,
    id_viaje               INTEGER REFERENCES viajes(id_viaje),
    tipo_alerta            VARCHAR(30),
    nivel_severidad        VARCHAR(15),
    accion_sugerida        VARCHAR(20),
    mensaje                TEXT,
    detalle_recomendacion  TEXT,
    lat_posicion           DOUBLE PRECISION,
    lng_posicion           DOUBLE PRECISION,
    probabilidad_rf_actual DOUBLE PRECISION,
    dato_con_latencia      BOOLEAN,
    timestamp_generacion   TIMESTAMPTZ,
    leida                  BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_alertas_viaje ON alertas_viaje(id_viaje, timestamp_generacion DESC);
```

#### ML Service — Nuevo endpoint POST /monitorear/trayecto

Compara el snapshot inicial con las condiciones actuales.

**Lógica de nivel_cambio:**

| Delta RF vs inicio | Con latencia | nivel_cambio |
|---|---|---|
| menor a 0.10 | No | ESTABLE |
| 0.10 a 0.25 | No | MODERADO |
| mayor a 0.25 | No | SIGNIFICATIVO |
| Cualquiera | Sí | Sube un nivel (máx CRITICO) |
| RF actual mayor a 0.85 | cualquiera | CRITICO siempre |

Variable de entorno: `LATENCIA_UMBRAL_MINUTOS=15`

#### Backend — Nuevos componentes

**CondicionesSnapshotRepository** — JOOQ DAO: save(), findByViajeId()

**AlertaViajeRepository** — JOOQ DAO: save(), findByViajeId(), marcarComoLeida()

**AlertaGeneratorService** (clase estática, patrón TripPlannerOrchestrator):

| nivel_cambio | accion_sugerida | Mensaje exacto al usuario |
|---|---|---|
| ESTABLE | ninguna | null (sin alerta) |
| MODERADO | CONTINUAR | "Condiciones climáticas favorables, continuar trayecto" |
| SIGNIFICATIVO | NUEVA_RUTA | "Nueva ruta a considerar" |
| SIGNIFICATIVO con RF mayor a 0.6 | FENOMENO_POSIBLE | "Fenómeno climático posible en tu zona" |
| CRITICO | CANCELAR_VIAJE | "SE RECOMIENDA CANCELAR VIAJE" |

**TripMonitorService** + TripMonitorServiceImpl:

```
evaluarPosicion(idViaje, lat, lng) devuelve MonitoreoResponseDTO
  1. findSnapshot(idViaje)
  2. weatherMLService.predictRainForLocation(lat, lng)
  3. POST /monitorear/trayecto al ML service
  4. AlertaGeneratorService.generar(mlRes)
  5. alertaRepository.save(alerta) — solo si hay alerta nueva
  6. return alertaNueva y condicionesActuales
```

**ViajeMonitorController** — Endpoints bajo /api/viajes/{id}/:

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | /api/viajes/{id}/posicion | JWT | Reporta posición; retorna alerta si existe |
| GET | /api/viajes/{id}/alertas | JWT | Lista historial de alertas |
| PATCH | /api/viajes/{id}/alertas/{idAlerta}/leer | JWT | Marca alerta como leída |

**Modificación a ViajeUseCase.planificarViaje()**: Al finalizar, guardar el condiciones_snapshot.

**Nuevos DTOs:** PosicionRequestDTO, MonitoreoResponseDTO, AlertaViajeDTO

#### Frontend — Modificaciones a EnRuta.jsx

**Polling adaptativo:**
- Sin alertas / VERDE: cada 60 segundos
- AMARILLO / PRECAUCION: cada 30 segundos
- ROJO / CRISIS: detener polling

**Componente RecomendacionBanner.jsx:**

| nivel_severidad | Presentación |
|---|---|
| INFORMATIVA | Toast verde, esquina superior, se cierra en 6 s |
| PRECAUCION | Banner amarillo persistente sobre el mapa |
| PELIGRO | Modal con overlay semitransparente, ícono naranja |
| CRISIS | Full-screen rojo, texto grande, navigator.vibrate() |

Textos exactos que ve el usuario:
1. "Condiciones climáticas favorables, continuar trayecto"
2. "Nueva ruta a considerar"
3. "Fenómeno climático posible"
4. "SE RECOMIENDA CANCELAR VIAJE"

**client.js** — nuevas funciones: reportarPosicion(), obtenerAlertas(), marcarAlertaLeida()

---

### Bloque B: Capa de Calor Climático

#### Estrategia: Grid de muestreo local

1. Al iniciar el trayecto, generar grilla 5x5 (25 puntos, aprox 300m separación) centrada en posición actual.
2. Llamar a POST /api/weather/predict-grid con los 25 puntos.
3. Backend llama al ML service en paralelo (CompletableFuture) para los 25 puntos.
4. Frontend recibe lista de {lat, lng, probabilidadRf} y renderiza HeatmapLayer de Google Maps.
5. Refrescar cada 3 minutos (no en cada update GPS).

#### DB
Sin cambios — datos efímeros.

#### Backend — Nuevo endpoint POST /api/weather/predict-grid

```
Request:  { "puntos": [{ "lat": ..., "lng": ... }] }
Response: { "resultados": [{ "lat": ..., "lng": ..., "probabilidadRf": ... }] }
```

Implementado en WeatherController + WeatherMLService.predictGridForArea().

#### Frontend

- HeatmapLayer con opacidad 0.45 (alta transparencia).
- Gradiente: verde (0%) → amarillo (50%) → rojo (85%+).
- Toggle para mostrar/ocultar la capa (ícono de nube en esquina del mapa).

Requiere activar la librería visualization en el APIProvider de App.jsx.

---

## Sprint 5.3 — Múltiples Paradas en un Viaje

### Objetivo
Permitir al usuario agregar paradas intermedias al planificar. El sistema calcula la ruta pasando por todos los waypoints en orden.

### DB — Migración V5

**Tabla paradas_viaje**

```sql
CREATE TABLE paradas_viaje (
    id_parada                    SERIAL PRIMARY KEY,
    id_viaje                     INTEGER NOT NULL REFERENCES viajes(id_viaje) ON DELETE CASCADE,
    orden                        SMALLINT NOT NULL,
    lat                          DOUBLE PRECISION NOT NULL,
    lng                          DOUBLE PRECISION NOT NULL,
    nombre                       VARCHAR(255),
    tiempo_llegada_estimado_min   SMALLINT,
    finalizado                   BOOLEAN DEFAULT FALSE,
    hora_llegada_real            TIMESTAMPTZ,
    UNIQUE (id_viaje, orden)
);

CREATE INDEX idx_paradas_viaje ON paradas_viaje(id_viaje, orden);
```

### Backend

**TripRequestDTO** — agregar campo `List<LocationPointDTO> paradas` (lista vacía = viaje directo, compatible hacia atrás).

**ViajeUseCase.planificarViaje()** — si paradas no está vacío:
- Llamar a Google Directions con waypoints[].
- legs[] devueltos → sumar tiempos por segmento.
- Persistir paradas en paradas_viaje con orden y tiempo_llegada_estimado_min acumulado.

**ParadaViajeRepository** — JOOQ DAO: saveAll(), findByViajeId(), marcarParadaFinalizada()

**ViajeController — nuevos endpoints:**

| Método | Ruta | Descripción |
|---|---|---|
| GET | /api/viajes/{id}/paradas | Lista las paradas de un viaje |
| PATCH | /api/viajes/{id}/paradas/{orden}/finalizar | Marca una parada como visitada |

**TripResponseDTO** — agregar campo `List<ParadaDTO> paradas`.

### Frontend

**PlanificarViaje.jsx**
- Botón "+ Agregar parada" bajo el origen.
- Lista dinámica de inputs con Google Places Autocomplete por parada.
- Botón × por parada para eliminarla.
- Botones arriba/abajo para reordenar.
- Máximo 5 paradas intermedias.

**ResultadoViaje.jsx**
- Sección "Itinerario" con todas las paradas y tiempo estimado de llegada a cada una.

**EnRuta.jsx**
- Marcadores numerados para cada parada intermedia.
- Auto-marcar parada como finalizada al acercarse (menos de 100m).
- Banner "LLEGANDO A PARADA N" cuando corresponde.
- Polyline segmentada: gris (ya recorrido) vs accent (pendiente).

---

## Dependencias entre Sprints

```
Sprint 5.0 (UI Refactor)
  Sprint 5.1 (GPS en vivo)
        Sprint 5.2A (Recomendaciones)
        Sprint 5.2B (Capa de calor)
  Sprint 5.3 (DB + Backend paradas puede empezar en paralelo)
        Sprint 5.3 Frontend paradas — después de Sprint 5.1
```

---

## Resumen de cambios por capa

### Base de datos

| Migración | Qué crea | Sprint |
|---|---|---|
| V4 | condiciones_snapshot, alertas_viaje | 5.2A |
| V5 | paradas_viaje | 5.3 |

### Backend Spring Boot

| Componente | Tipo | Sprint |
|---|---|---|
| TripResponseDTO.StepDTO (campos faltantes) | Modificado | 5.1 |
| CondicionesSnapshotRepository | Nuevo | 5.2A |
| AlertaViajeRepository | Nuevo | 5.2A |
| AlertaGeneratorService | Nuevo | 5.2A |
| TripMonitorService + Impl | Nuevo | 5.2A |
| ViajeMonitorController | Nuevo | 5.2A |
| ViajeUseCase (guardar snapshot) | Modificado | 5.2A |
| POST /api/weather/predict-grid | Nuevo | 5.2B |
| ParadaViajeRepository | Nuevo | 5.3 |
| ViajeUseCase (waypoints) | Modificado | 5.3 |
| ViajeController (paradas endpoints) | Modificado | 5.3 |
| TripRequestDTO (campo paradas) | Modificado | 5.3 |
| TripResponseDTO (campo paradas) | Modificado | 5.3 |

### ML Service FastAPI

| Componente | Tipo | Sprint |
|---|---|---|
| POST /monitorear/trayecto | Nuevo | 5.2A |

### Frontend React

| Componente | Tipo | Sprint |
|---|---|---|
| index.css (tokens duales dark/light) | Modificado | 5.0 |
| ThemeToggle.jsx | Nuevo | 5.0 |
| App.jsx (init tema) | Modificado | 5.0 |
| NavigationHeader.jsx | Nuevo | 5.1 |
| NavigationPanel.jsx | Nuevo | 5.1 |
| EnRuta.jsx (heading, snap-to-road, ETA, turn-by-turn) | Modificado mayor | 5.1 |
| RecomendacionBanner.jsx | Nuevo | 5.2A |
| EnRuta.jsx (polling + alertas) | Modificado | 5.2A |
| client.js (3 nuevas funciones) | Modificado | 5.2A |
| HeatmapLayer en EnRuta.jsx | Modificado | 5.2B |
| PlanificarViaje.jsx (UI de paradas) | Modificado mayor | 5.3 |
| ResultadoViaje.jsx (itinerario) | Modificado | 5.3 |
| EnRuta.jsx (marcadores paradas, auto-finalizar) | Modificado | 5.3 |

---

## Notas técnicas importantes

1. **@vis.gl/react-google-maps ya instalado** — HeatmapLayer requiere activar la librería visualization en el APIProvider de App.jsx.

2. **El campo pasos (steps) ya viene del backend** — verificar que htmlInstructions y startLocation estén mapeados en TripResponseDTO antes de Sprint 5.1.

3. **watchPosition ya implementado** en EnRuta.jsx por Nicolás — Sprint 5.1 extiende lo existente para rotar el marcador y hacer pan-to.

4. **coords.heading** es null en dispositivos sin sensor o en reposo — manejar fallback (conservar última rotación).

5. **Google Directions Waypoints** — límite de 25 waypoints en API; limitar UI a 5 paradas intermedias.

6. **JOOQ regeneration** necesaria tras V4 y V5 (./gradlew generateJooq con postgres corriendo).

---

*MDVA — Plan de Implementación Sprint 5 · Abril 2026*
