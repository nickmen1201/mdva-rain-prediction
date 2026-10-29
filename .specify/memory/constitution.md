<!--
Sync Impact Report
- Version change: (template sin ratificar) → 1.0.0
- Principios: plantilla vacía → I–VII definidos a partir de la "Engineering Constitution"
  del autor (v1.0.0, 2026-07-24) con los perfiles SWE, Data Eng y DS/ML activos.
- Secciones agregadas: "Restricciones técnicas y de datos", "Flujo de trabajo y quality gates".
- Secciones eliminadas: ninguna.
- Contexto del proyecto (diagnóstico, estructura objetivo, requisitos a preservar) vive en
  `.specify/memory/charter.md` y es de lectura obligatoria para toda spec.
- TODOs diferidos: ninguno.
-->

# MDVA Constitution

Reglas de *cómo* construimos. La spec gobierna el *qué*. Si el código viola este archivo, el
código está mal; si este archivo y una spec chocan, se detiene el trabajo y se pregunta.

**Palabras clave:** MUST / NEVER = bloquea el merge. DEFAULT / PREFER = la opción a falta de una
razón documentada (se puede cambiar con una frase en la spec o en un ADR).

Perfiles activos: **[x] SWE  [x] Data Eng  [x] DS/ML**

## Core Principles

### I. La intención fluye cuesta abajo

spec → plan → contrato → tareas → código. Un cambio de comportamiento entra por la spec y vuelve
a fluir; NEVER se parchea en el código dejando la spec desactualizada. Comportamiento no
especificado → se detiene y se pregunta; NEVER se inventa. Los requisitos funcionales listados en
`.specify/memory/charter.md` §4 MUST preservarse salvo que una spec aprobada los cambie
explícitamente.

### II. Reproducible desde un checkout limpio

Todo resultado se reproduce con comandos documentados (`make …`, `docker compose …`). Lockfiles
commiteados, versiones de herramientas fijadas, semillas fijas donde el determinismo es factible.
NEVER rutas absolutas ni rutas fuera del repo. El stack completo MUST levantar sin ninguna API key
de pago (NEVER depender de un servicio que exija tarjeta de crédito para correr el proyecto).

### III. Secretos fuera del repo

Credenciales solo desde variables de entorno (`.env` local gitignored, plantilla en
`.env.example`). La CI MUST fallar ante una credencial filtrada (escáner de secretos en cada push).

### IV. Contract-first

Toda interfaz entre servicios tiene un contrato lintable (OpenAPI / JSON Schema) escrito y
validado *antes* del código. Ningún endpoint existe en código sin estar en el contrato. Cada
operación declara todos sus resultados, errores incluidos; los errores HTTP usan Problem Details
(RFC 7807) (DEFAULT). Los cambios de contrato se clasifican como aditivos o rompientes y se
muestran como diff antes de codificar. Tests de contrato validan el código en ejecución contra el
archivo. Las dependencias apuntan hacia adentro: el dominio NEVER depende de infraestructura; se
mapea a DTOs en el borde.

### V. Contratos de datos y pipeline raw → interim → processed

Cada dataset tiene un contrato explícito y versionado (columnas, tipos, unidades SI, rangos, zona
horaria). `data/raw` es inmutable; las transformaciones son idempotentes y re-ejecutables. Los
quality gates (conteos, nulos, unicidad, rangos, frescura) corren *dentro* del pipeline y un gate
fallido detiene la promoción aguas abajo.

### VI. Evaluación honesta de ML y paridad train/serve

Se versionan datos + código + configuración juntos; un resultado que no se puede reproducir no
existe. Toda corrida de entrenamiento queda registrada (parámetros, versión de datos, versión de
código, métricas) en un archivo generado por código. Se evalúa en un holdout **temporal** contra
baselines definidos (climatología y persistencia como mínimo); NEVER se reporta desempeño sobre
datos de entrenamiento. Las features de entrenamiento e inferencia salen de **un único módulo**
(`mdva/features.py`) y de la **misma fuente de datos**; un test MUST demostrar la paridad. NEVER se
rellena con ceros o promedios una feature desconocida en inferencia. Las probabilidades usadas
contra umbrales de negocio MUST estar calibradas.

### VII. Sin datos fabricados

Ningún servicio inventa insumos (elevaciones sintéticas, clima "promedio" de respaldo,
probabilidades = intensidad × constante). Si un insumo falta, la respuesta lo declara (campo de
degradación o error RFC 7807).

## Restricciones técnicas y de datos

- Estructura del repo: **Cookiecutter Data Science v2**; paquete Python `mdva/`; servicios en
  `services/`, aplicaciones en `apps/` (detalle en el charter §2).
- Timestamps almacenados y transmitidos en **UTC, tz-aware, ISO 8601**. La hora local
  (`America/Bogota`) solo se deriva como feature del modelo, dentro de `mdva/features.py`.
- Identificadores nuevos que crucen un límite de servicio: UUIDv7/ULID (DEFAULT). Las tablas
  existentes con IDs secuenciales se conservan; no se migran salvo spec explícita.
- UTF-8 en todo el repo.
- Fuente meteorológica única para entrenamiento e inferencia: **Open-Meteo** (sin API key).
  Geocodificación: Nominatim/OSM. Mapas: MapLibre + teselas OSM. Rutas: routing service propio.
- Notebooks exploran; todo lo repetible se promueve a `mdva/` con tests. NEVER un notebook en
  producción.
- Cada dependencia nueva se justifica en una línea (por qué, y por qué no la stdlib) en el plan.
- Versiones exactas fijadas en un solo lugar por ecosistema (`pyproject.toml` + `uv.lock`,
  `package-lock.json`, `build.gradle.kts`).

## Flujo de trabajo y quality gates

- Cada spec recorre todas las fases de spec-kit: specify → clarify → plan → tasks → analyze →
  implement. Ninguna implementación empieza antes de que `analyze` quede sin hallazgos CRITICAL.
- Gate de revisión: el agente ejecuta la revisión y verificación de cada spec antes de darla por
  lista (tests verdes, stack levantado y smoke test de punta a punta cuando la spec toca
  servicios). Decisión del autor del 2026-10-28; reemplaza la revisión humana del primer slice.
- Commits: Conventional Commits; un commit por fase de spec o por tarea, con push a `main`.
  Los commits se atribuyen solo al autor del repositorio: NEVER trailers `Co-Authored-By` ni
  firmas de herramientas.
- Todo lo verificable por linter, type-checker o test MUST verificarse ahí: `ruff` (Python),
  `eslint` (Frontend), Gradle `test` (Backend), `pytest`. CI en rojo bloquea el merge.
- Ambigüedades resueltas sin el autor se documentan en la sección *Clarifications* de la spec,
  eligiendo la opción más conservadora (la que preserva el comportamiento existente).

## Governance

Esta constitución prevalece sobre cualquier otra práctica del repo. Las enmiendas se hacen por
commit que modifica este archivo, actualiza el Sync Impact Report e incrementa la versión
(SemVer: MAJOR si elimina o redefine un principio, MINOR si agrega uno o amplía guía de forma
material, PATCH si aclara). La versión de API (lo que cambia para consumidores) se mantiene
distinta de la versión de artefacto (lo que cambia para el equipo). Toda spec y todo plan MUST
incluir un *Constitution Check* que cite los principios afectados. Guía operativa en
`CLAUDE.md`; contexto del proyecto en `.specify/memory/charter.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
