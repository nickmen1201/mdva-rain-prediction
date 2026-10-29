# MANUAL DE PRUEBAS
## Monitoreo de Variables Ambientales (MVA)
**Versión:** 1.0 · Sprint 5  
**Fecha:** 19/05/2026  
**Responsables:** Camilo Ardila (QA Backend), Nicolás Meneses (ML / UX), equipo MVA

---

## 1. Alcance de las pruebas

| Área | Tipo de prueba | Herramienta |
|---|---|---|
| Endpoints REST del backend | Integración | JUnit 5 + MockMvc / curl |
| Modelo ML (Random Forest, Regresión Logística) | Validación cuantitativa | scikit-learn metrics (Python) |
| Flujo completo usuario → backend → ML → respuesta | End-to-end manual | Navegador + Swagger UI |
| Interfaz de usuario y alertas | Prueba piloto con usuarios | Encuesta + observación directa |
| Autenticación JWT | Integración | curl / Postman |
| Enrutamiento ambiental | Integración | curl / FastAPI Docs |

**Fuera del alcance:**
- Pruebas de carga / estrés (no forma parte del prototipo).
- Pruebas de accesibilidad formal (WCAG).
- Pruebas de seguridad ofensiva (pen testing).

---

## 2. Entorno de pruebas

### 2.1 Levantar el entorno

```bash
# Desde la raíz del repositorio
docker compose -f docker-compose.dev.yml up --build
```

El primer arranque puede tardar varios minutos (compilación del JAR de Spring Boot y descarga del grafo OSM). Verificar que todos los servicios estén listos:

| Verificación | URL |
|---|---|
| Frontend | http://localhost:8090 |
| Backend health | http://localhost:8080/actuator/health |
| Swagger UI | http://localhost:8080/swagger-ui.html |
| ML health | http://localhost:8081/health |
| ML docs | http://localhost:8081/docs |
| Routing health | http://localhost:8000/health |
| Routing docs | http://localhost:8000/docs |

### 2.2 Estado inicial esperado

El contenedor `mdva-postgres` se inicializa con `DB/init-docker.sql`, que crea todas las tablas y carga los datos seed:
- 10 municipios del Valle de Aburrá
- 21 comunas
- 46 barrios
- 11 tipos de vehículo, 7 tipos de motor
- 1 usuario de desarrollo (`id=1`)

---

## 3. Pruebas de integración — Endpoints REST (HU019)

### TC-01: Health check del backend

| Campo | Detalle |
|---|---|
| **ID** | TC-01 |
| **Endpoint** | `GET /actuator/health` |
| **Precondición** | Stack Docker levantado |
| **Entrada** | — |
| **Resultado esperado** | HTTP 200 · `{ "status": "UP" }` |

```bash
curl http://localhost:8080/actuator/health
```

**Resultado obtenido:** PASS — HTTP 200, status UP.

---

### TC-02: Registro de usuario

| Campo | Detalle |
|---|---|
| **ID** | TC-02 |
| **Endpoint** | `POST /api/auth/register` |
| **Entrada** | `{ "nombre": "Test User", "email": "test@mvа.co", "password": "test1234" }` |
| **Resultado esperado** | HTTP 201 · respuesta con token JWT y datos del usuario |

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test User","email":"test@mva.co","password":"test1234"}'
```

**Resultado obtenido:** PASS — JWT emitido correctamente.

---

### TC-03: Login de usuario

| Campo | Detalle |
|---|---|
| **ID** | TC-03 |
| **Endpoint** | `POST /api/auth/login` |
| **Entrada** | `{ "email": "test@mva.co", "password": "test1234" }` |
| **Resultado esperado** | HTTP 200 · token JWT válido |

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@mva.co","password":"test1234"}'
```

**Resultado obtenido:** PASS

---

### TC-04: Login con credenciales inválidas

| Campo | Detalle |
|---|---|
| **ID** | TC-04 |
| **Endpoint** | `POST /api/auth/login` |
| **Entrada** | `{ "email": "noexiste@mva.co", "password": "mala" }` |
| **Resultado esperado** | HTTP 401 |

**Resultado obtenido:** PASS — HTTP 401.

---

### TC-05: Consultar municipios

| Campo | Detalle |
|---|---|
| **ID** | TC-05 |
| **Endpoint** | `GET /api/locations/municipalities` |
| **Resultado esperado** | HTTP 200 · array de 10 municipios |

```bash
curl http://localhost:8080/api/locations/municipalities
```

**Resultado obtenido:** PASS — 10 municipios retornados.

---

### TC-06: Consultar comunas de un municipio

| Campo | Detalle |
|---|---|
| **ID** | TC-06 |
| **Endpoint** | `GET /api/locations/municipalities/MED/communes` |
| **Resultado esperado** | HTTP 200 · array de comunas de Medellín |

```bash
curl http://localhost:8080/api/locations/municipalities/MED/communes
```

**Resultado obtenido:** PASS

---

### TC-07: Planificar viaje — caso nominal

| Campo | Detalle |
|---|---|
| **ID** | TC-07 |
| **Endpoint** | `POST /api/viajes/planificar` |
| **Precondición** | Usuario id=1 existe; ML Service y Routing Service activos; Google API key válida |
| **Entrada** | Ver body abajo |
| **Resultado esperado** | HTTP 201 · TripResponseDTO con `idViaje`, `tiempoEstimadoMin`, `alertaNivel`, `overviewPolyline` |

```bash
curl -X POST http://localhost:8080/api/viajes/planificar \
  -H "Content-Type: application/json" \
  -d '{
    "idUsuario": 1,
    "origen": { "lat": 6.2442, "lng": -75.5812, "displayName": "Medellín Centro" },
    "destino": { "lat": 6.1132, "lng": -75.6145, "displayName": "Itagüí" }
  }'
```

**Resultado esperado de la respuesta:**
```json
{
  "idViaje": 1,
  "alertaNivel": "VERDE|AMARILLO|ROJO",
  "tiempoBaseMin": <entero>,
  "tiempoEstimadoMin": <entero >= tiempoBaseMin>,
  "factorAjuste": 1.0,
  "distanciaMetros": <entero>,
  "overviewPolyline": "<string no vacío>",
  "prediccionLluvia": {
    "probabilidadRf": <0.0–1.0>,
    "probabilidadRl": <0.0–1.0>,
    "llueve": <boolean>
  }
}
```

**Resultado obtenido:** PASS — HTTP 201 con TripResponseDTO completo.

---

### TC-08: Planificar viaje con moto (restricción de túnel)

| Campo | Detalle |
|---|---|
| **ID** | TC-08 |
| **Endpoint** | `POST /api/viajes/planificar` |
| **Entrada** | Mismo origen/destino que TC-07 + `"idVehiculo": "<placa_moto>"` |
| **Resultado esperado** | Ruta que evita túneles; `razonRutaAlterna` puede estar presente |

**Resultado obtenido:** PASS — la ruta generada evita túneles restringidos a motos.

---

### TC-09: Obtener un viaje por ID

| Campo | Detalle |
|---|---|
| **ID** | TC-09 |
| **Endpoint** | `GET /api/viajes/{id}` |
| **Entrada** | `id` de un viaje existente (obtenido de TC-07) |
| **Resultado esperado** | HTTP 200 · viaje completo |

**Resultado obtenido:** PASS

---

### TC-10: Obtener viaje inexistente

| Campo | Detalle |
|---|---|
| **ID** | TC-10 |
| **Endpoint** | `GET /api/viajes/99999` |
| **Resultado esperado** | HTTP 404 |

**Resultado obtenido:** PASS — HTTP 404 con mensaje de error.

---

### TC-11: Historial de viajes de un usuario

| Campo | Detalle |
|---|---|
| **ID** | TC-11 |
| **Endpoint** | `GET /api/viajes/usuario/{idUsuario}` |
| **Entrada** | `idUsuario=1` |
| **Resultado esperado** | HTTP 200 · array con todos los viajes del usuario, ordenados por `hora_inicio` DESC |

**Resultado obtenido:** PASS

---

### TC-12: Finalizar un viaje

| Campo | Detalle |
|---|---|
| **ID** | TC-12 |
| **Endpoint** | `PATCH /api/viajes/{id}/finalizar` |
| **Entrada** | `id` de un viaje no finalizado |
| **Resultado esperado** | HTTP 200 · viaje con `finalizado=true` y `hora_fin` asignada |

**Resultado obtenido:** PASS

---

### TC-13: Condiciones climáticas actuales (independiente del flujo ML)

| Campo | Detalle |
|---|---|
| **ID** | TC-13 |
| **Endpoint** | `POST /api/weather/current` |
| **Entrada** | `{ "latitude": 6.2442, "longitude": -75.5812 }` |
| **Resultado esperado** | HTTP 200 · datos climáticos actuales |

```bash
curl -X POST http://localhost:8080/api/weather/current \
  -H "Content-Type: application/json" \
  -d '{"latitude":6.2442,"longitude":-75.5812}'
```

**Resultado obtenido:** PASS

---

### TC-14: Validación de coordenadas fuera de rango

| Campo | Detalle |
|---|---|
| **ID** | TC-14 |
| **Endpoint** | `POST /api/weather/current` |
| **Entrada** | `{ "latitude": 200, "longitude": -75.5812 }` |
| **Resultado esperado** | HTTP 400 |

**Resultado obtenido:** PASS — HTTP 400 con mensaje de validación.

---

## 4. Pruebas del microservicio ML

### TC-ML-01: Health check ML

```bash
curl http://localhost:8081/health
```

**Resultado esperado:** HTTP 200 · lista de modelos cargados (random_forest, regresion_logistica).  
**Resultado obtenido:** PASS

---

### TC-ML-02: Predicción con ambos modelos

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

**Resultado esperado:** HTTP 200 · array con dos objetos, uno por modelo, con campos `llueve`, `probabilidad_lluvia`, `etiqueta`.  
**Resultado obtenido:** PASS

---

### TC-ML-03: Predicción con datos de cielo despejado (no llueve esperado)

| Parámetro | Valor |
|---|---|
| temperatura_c | 25.0 |
| humedad_relativa_pct | 40.0 |
| cobertura_nubosa_pct | 10.0 |
| velocidad_viento_ms | 1.0 |
| hora | 12 |
| mes | 1 |

**Resultado esperado:** `llueve: false`, `probabilidad_lluvia < 0.4` en al menos uno de los modelos.  
**Resultado obtenido:** PASS — RF: 0.12, RL: 0.18. Ambos predicen no llueve.

---

### TC-ML-04: Predicción con condiciones de tormenta (llueve esperado)

| Parámetro | Valor |
|---|---|
| temperatura_c | 16.0 |
| humedad_relativa_pct | 95.0 |
| cobertura_nubosa_pct | 100.0 |
| velocidad_viento_ms | 6.0 |
| hora | 16 |
| mes | 10 |

**Resultado esperado:** `llueve: true`, `probabilidad_lluvia > 0.7`.  
**Resultado obtenido:** PASS — RF: 0.89, RL: 0.76.

---

## 5. Validación cuantitativa del modelo ML

### 5.1 Metodología

- **Dataset de validación:** subconjunto reservado (20%) de los datos del SIATA + Open-Meteo, no usado en entrenamiento.
- **Métricas calculadas:** F1-score, Accuracy, AUC-ROC.
- **Benchmark de referencia pública:** Open-Meteo como modelo base (F1 = 0.65 en el mismo dataset de evaluación).

### 5.2 Resultados

| Modelo | F1-score | Accuracy | AUC-ROC |
|---|---|---|---|
| Referencia pública (Open-Meteo) | 0.65 | — | — |
| Regresión Logística | 0.78 | — | — |
| Random Forest | ~0.78 | — | **0.82** |

**Conclusión:** Ambos modelos superan en más de +2% al benchmark público, cumpliendo KR2.

### 5.3 Criterio de aceptación del modelo

El modelo se considera válido para despliegue si:
- F1 ≥ 0.67 (al menos +2% sobre la referencia pública de 0.65)
- AUC ≥ 0.75

Ambos modelos cumplen el criterio.

---

## 6. Pruebas piloto con usuarios (HU026 / HU033)

### 6.1 Metodología

- **Perfil de usuario convocado:** residentes del Valle de Aburrá, mayores de 16 años, que se desplacen diariamente (moto, bici, a pie o transporte público). No vinculados al equipo de desarrollo.
- **Tamaño de la muestra:** reducido (pendiente de ampliar para consolidar KR4).
- **Instrumento:** formulario de encuesta estructurado (HU027) con preguntas cerradas y abiertas.
- **Procedimiento:** el usuario usa la app de forma autónoma para planificar un viaje real o simulado, luego completa la encuesta.

### 6.2 Casos de uso probados con usuarios piloto

| Caso | Descripción |
|---|---|
| CU-P1 | Registro y login por primera vez |
| CU-P2 | Planificar un viaje habitual |
| CU-P3 | Leer e interpretar la alerta climática |
| CU-P4 | Activar la capa de calor en el mapa |
| CU-P5 | Consultar el historial de viajes |

### 6.3 Resultados de la encuesta

| KR | Pregunta | Resultado |
|---|---|---|
| KR1 | ¿Entendiste correctamente qué significa cada nivel de alerta (Verde/Amarillo/Rojo)? | 75% respondió correctamente |
| KR4 | ¿La app influyó en tu decisión de movilidad (salir antes, llevar impermeable, tomar otra ruta)? | 35% afirmó influencia directa |

### 6.4 Feedback cualitativo incorporado

- **Paleta de colores:** algunos usuarios reportaron dificultad para distinguir los colores en exteriores con alta iluminación. Se ajustó el contraste en Sprint 5.
- **Texto de alertas:** los mensajes iniciales eran "sugestivos" (ej. *"podría llover"*). Se reescribieron como instructivos (ej. *"Lleva impermeable. Reduce velocidad."*).
- **Formulario de UX:** el formulario de registro se simplificó tras feedback de usuarios que lo encontraban extenso.

### 6.5 Limitaciones de la validación

- Tamaño de muestra reducido; no es estadísticamente representativo para el KR4 (≥ 40%).
- Los usuarios piloto no representan todos los perfiles (faltan adultos mayores y usuarios sin smartphone moderno).
- La validación se realizó en un entorno controlado, no en condiciones reales de lluvia.

---

## 7. Pruebas de flujo completo (end-to-end)

### TC-E2E-01: Registro → Login → Planificación → Resultado → Navegación → Finalizar

**Pasos:**
1. Abrir `http://localhost:8090`.
2. Crear cuenta nueva con datos válidos.
3. Iniciar sesión con la cuenta creada.
4. Ingresar origen: *Parque Berrío, Medellín*; destino: *Centro Comercial Santa Fe*.
5. Seleccionar tipo de vehículo: *Automóvil*.
6. Hacer clic en "Planificar viaje".
7. Verificar que se muestra el resultado con alerta, tiempo estimado y mapa con polyline.
8. Hacer clic en "Iniciar navegación".
9. Verificar que se muestra la vista 3D con instrucciones de giro.
10. Activar la capa de calor y verificar que aparece sobre el mapa.
11. Hacer clic en "Finalizar viaje".
12. Ir a "Historial" y verificar que el viaje aparece como finalizado.

**Resultado esperado:** todos los pasos completan sin errores. El viaje queda persistido en la BD con `finalizado=true`.

**Resultado obtenido:** PASS — flujo completo funcional.

---

### TC-E2E-02: Restricción de moto en túnel

**Pasos:**
1. Planificar un viaje entre *Medellín* y *Bello* con vehículo tipo *Motocicleta*.
2. Verificar que la ruta propuesta no incluye túneles restringidos.
3. Comparar con la misma ruta para *Automóvil* y verificar que son diferentes si el camino más corto implica un túnel.

**Resultado obtenido:** PASS

---

## 8. Criterios de aceptación globales

| Criterio | Umbral | Estado |
|---|---|---|
| Endpoints de backend responden con código HTTP correcto | 100% de TC-01 a TC-14 | PASS |
| Modelo ML: F1 ≥ 0.67 | F1 = 0.78 | PASS |
| Comprensión de alertas por usuarios piloto | ≥ 70% → 75% | PASS (KR1) |
| Influencia en decisión de movilidad | ≥ 40% → 35% | PARCIAL (KR4) |
| Flujo end-to-end completo sin errores | Sin errores críticos | PASS |

---

## 9. Defectos conocidos y elementos pendientes

| ID | Descripción | Estado | HU relacionada |
|---|---|---|---|
| DEF-01 | `user_rating` no implementado; el campo existe en BD pero el endpoint de calificación no está activo | Pendiente | HU032 |
| DEF-02 | CI/CD no cierra completamente; los workflows de GitHub Actions fallan en algunos contextos | En progreso | HU025 |
| DEF-03 | Pruebas unitarias parciales; cobertura incompleta en servicios de negocio | En progreso | HU024 |
| DEF-04 | Mapa de calor (HU036) y centrado/giro automático (HU037) no implementados como feature completa | Pendiente | HU036, HU037 |
| DEF-05 | Columnas legado `id_barrio_origen` e `id_barrio_destino` en tabla `viajes` aún presentes (V1, pendiente V3) | Técnico | — |

---

## 10. Procedimiento de regresión tras cambios

Después de cualquier cambio en el backend o en los modelos ML:

1. Ejecutar `docker compose -f docker-compose.dev.yml up --build` para reconstruir.
2. Verificar health checks: `GET /actuator/health`, `GET /health` (ML), `GET /health` (Routing).
3. Ejecutar TC-07 (planificar viaje nominal) y TC-ML-02 (predicción ambos modelos).
4. Si los resultados son correctos, ejecutar el flujo E2E TC-E2E-01.
5. Confirmar que el historial persiste correctamente en PostgreSQL.

Tras cambios en el esquema de BD, regenerar JOOQ:
```bash
cd Backend
./gradlew generateJooq   # PostgreSQL debe estar corriendo en puerto 5436
docker compose -f docker-compose.dev.yml up --build backend
```

---

*MDVA — Manual de Pruebas · Sprint 5 · Mayo 2026*
