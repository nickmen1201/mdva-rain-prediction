# Feature Specification: Tooling Python, calidad automatizada y CI

**Feature Branch**: `002-python-tooling-ci` (trabajo directo en `main`)

**Created**: 2026-10-28

**Status**: Implemented (2026-10-28)

**Input**: User description: "Fijar versiones y entorno reproducible de Python, automatizar lint/format/tests y escaneo de secretos en CI, con pruebas de caracterización del servicio ML antes de refactorizarlo (charter R-38–R-41; constitución II, III y quality gates)."

## User Scenarios & Testing *(mandatory)*

Usuarios: **quien desarrolla** (hoy el autor; mañana cualquiera que clone el repo) y **quien revisa** el portafolio, que mira la CI como señal de calidad.

### User Story 1 - Entorno Python reproducible con un comando (Priority: P1)

Quien clona el repo instala exactamente las mismas versiones de librerías que corren hoy en los contenedores, para el paquete de ciencia de datos y para cada servicio, con un solo comando por proyecto y sin adivinar versiones.

**Why this priority**: la constitución (II) exige versiones fijadas y lockfiles. Hoy el routing service no fija ninguna versión y ya corre con una versión de scikit-learn distinta a la que serializó su modelo (H-13).

**Independent Test**: desde un clon limpio, instalar cada proyecto con el comando documentado y comparar las versiones instaladas con las del lockfile.

**Acceptance Scenarios**:

1. **Given** un clon limpio, **When** se instala el entorno del paquete `mdva` o de cualquier servicio, **Then** las versiones instaladas coinciden exactamente con el lockfile versionado.
2. **Given** los lockfiles, **When** se construyen las imágenes de los servicios, **Then** las imágenes instalan exactamente las versiones bloqueadas.
3. **Given** las imágenes reconstruidas, **When** se ejecuta el smoke test, **Then** el resultado es idéntico a la línea base de la spec 001.

---

### User Story 2 - Cada push se verifica automáticamente (Priority: P1)

Cada push a `main` ejecuta lint y formato de Python, tests de Python, lint del Frontend y los checks existentes del Backend y del Frontend. Un check en rojo se ve en GitHub y bloquea el merge.

**Why this priority**: la constitución exige que todo lo verificable por herramienta se verifique ahí; hoy no existe ningún check de Python.

**Independent Test**: provocar una violación de lint en una rama local y comprobar que el comando de verificación falla; en `main`, comprobar que todos los checks pasan.

**Acceptance Scenarios**:

1. **Given** el código actual, **When** corre la CI, **Then** todos los jobs (Python, Backend, Frontend, secretos) terminan en verde.
2. **Given** un archivo Python con un import sin uso, **When** se ejecuta el comando de lint, **Then** falla indicando archivo y línea.
3. **Given** un desarrollador sin `make`, **When** sigue la documentación, **Then** puede ejecutar cada verificación con el comando equivalente.

---

### User Story 3 - Las credenciales filtradas se detectan (Priority: P2)

Si alguien commitea una credencial (API key, contraseña, token), la CI falla y señala el archivo.

**Why this priority**: constitución III ("la CI MUST fallar ante una credencial filtrada"); este repo ya tuvo una key y contraseñas expuestas (H-01).

**Independent Test**: ejecutar el escáner sobre el repo actual (debe pasar) y sobre un archivo de prueba con una credencial ficticia con formato real (debe fallar).

**Acceptance Scenarios**:

1. **Given** el historial actual del repo, **When** corre el escáner, **Then** no reporta hallazgos.
2. **Given** un commit con una credencial con formato real, **When** corre la CI, **Then** el job de secretos falla.

---

### User Story 4 - El comportamiento actual del servicio ML queda congelado en tests (Priority: P2)

Antes de refactorizar el servicio ML (spec 006), su comportamiento observable queda capturado en tests automáticos: endpoints, forma de las respuestas, validación de entradas y reglas de monitoreo de trayecto (charter RF-17, RF-22).

**Why this priority**: la constitución prohíbe refactorizar sin tests que pasen antes y después (charter P9).

**Independent Test**: ejecutar los tests del servicio ML contra el código actual; deben pasar.

**Acceptance Scenarios**:

1. **Given** el servicio ML actual, **When** se ejecutan sus tests, **Then** pasan y cubren health, predicción por modelo, predicción con ambos modelos, rechazo de hora y mes fuera de rango, y la tabla completa de reglas de monitoreo (ESTABLE, MODERADO, SIGNIFICATIVO, CRITICO, latencia y prevalencia de CRITICO).

### Edge Cases

- Dos servicios necesitan versiones distintas de la misma librería (p. ej. el servicio ML y el routing service usan versiones distintas de FastAPI y scikit-learn): cada uno conserva las suyas sin forzar una resolución común.
- Desarrolladores en Windows sin `make`: cada objetivo del Makefile tiene un comando equivalente documentado.
- El formateador cambia el estilo de archivos existentes: el cambio debe ser puramente de formato (sin cambios de comportamiento), verificado por los tests y el smoke test.
- Los notebooks no se someten al lint en esta spec (se documenta la exclusión).
- Los tests no pueden depender de red ni de descargar el grafo OSM.

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Un solo lockfile para todo Python o uno por proyecto? → A: Uno por proyecto (`mdva` en la raíz, `services/ml_api`, `services/routing_api`), porque los servicios ya corren con versiones incompatibles entre sí de FastAPI y scikit-learn; unificarlas cambiaría el comportamiento y es alcance de las specs 006 y 009.
- Q: ¿A qué versiones se fija cada servicio? → A: A las que corren hoy en los contenedores (`pip freeze` del 2026-10-28), para preservar el comportamiento.
- Q: ¿Qué reglas de lint se activan? → A: Errores de sintaxis y nombres (pyflakes), estilo básico (pycodestyle E/W) y orden de imports; longitud de línea 120. Reglas más estrictas se evalúan en specs posteriores.
- Q: ¿El cambio de `print` a logging (R-41) entra aquí? → A: No; se hace en las specs que reescriben esos archivos (005, 006, 009) para no tocar dos veces el mismo código.
- Q: ¿Cómo se ejecutan los objetivos en Windows sin `make`? → A: Makefile estándar de CCDS v2 más una tabla en el README con el comando equivalente de cada objetivo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El paquete `mdva` y cada servicio Python MUST declarar sus dependencias y fijarlas en un lockfile versionado, en un solo lugar por proyecto.
- **FR-002**: Las versiones bloqueadas de los servicios MUST coincidir con las que corren hoy en sus contenedores.
- **FR-003**: Las imágenes de los servicios MUST instalar sus dependencias desde el lockfile, sin resolver versiones en el momento de construir.
- **FR-004**: El repositorio MUST proveer un comando para cada una de estas acciones: instalar entornos, lint, formatear, tests, smoke test, levantar y bajar el stack, limpiar artefactos.
- **FR-005**: Todo el código Python versionado (excepto notebooks) MUST pasar el lint y el chequeo de formato.
- **FR-006**: La CI MUST ejecutar en cada push y pull request: lint y formato de Python, tests de cada proyecto Python, lint y build del Frontend, build y tests del Backend, escaneo de secretos.
- **FR-007**: El escaneo de secretos MUST revisar el historial completo y fallar ante cualquier hallazgo.
- **FR-008**: Los tests del servicio ML MUST cubrir los comportamientos listados en US4 y pasar sin red.
- **FR-009**: Los tests MUST poder ejecutarse sin el stack levantado y sin descargar datos externos.
- **FR-010**: El código del Frontend MUST pasar su lint existente sin desactivar reglas.
- **FR-011**: El comportamiento de los servicios MUST permanecer idéntico (smoke test igual a la línea base de la spec 001).

### Key Entities

- **Proyecto Python**: paquete `mdva`, servicio ML o routing service; tiene declaración de dependencias, lockfile y comando de tests.
- **Check de CI**: verificación automática con resultado verde/rojo visible en GitHub.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % de las dependencias Python de los 3 proyectos están fijadas a una versión exacta en lockfiles versionados; 0 dependencias sin versión.
- **SC-002**: Las versiones de las librerías principales (FastAPI, scikit-learn, pandas, NumPy, OSMnx, NetworkX) en las imágenes reconstruidas son idénticas a las del 2026-10-28.
- **SC-003**: Todos los checks de la CI terminan en verde en `main` al cerrar la spec.
- **SC-004**: El escáner de secretos detecta una credencial de prueba con formato real en un archivo nuevo (prueba local) y reporta 0 hallazgos en el historial actual.
- **SC-005**: Los tests del servicio ML cubren 100 % de las filas de la tabla de reglas de monitoreo del charter (RF-17).
- **SC-006**: El smoke test es idéntico a la línea base de la spec 001.

## Assumptions

- Python 3.11 es la versión de referencia (la de los contenedores).
- La CI corre en GitHub Actions (la ya configurada en el repo).
- El escáner de secretos se ejecuta con una herramienta de código abierto y gratuita para repositorios personales.
- Fuera de alcance: cambiar versiones de librerías, refactorizar los servicios, pre-commit hooks locales (se pueden agregar más adelante).
