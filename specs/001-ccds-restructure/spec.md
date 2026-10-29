# Feature Specification: Reestructuración Cookiecutter Data Science v2

**Feature Branch**: `001-ccds-restructure` (se trabaja directo sobre `main`, decisión del autor)

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Reorganizar el repositorio siguiendo Cookiecutter Data Science v2 y eliminar archivos innecesarios, sin cambiar el comportamiento del sistema (charter §2, §3.1, §3.2)."

## Clarifications

### Session 2026-10-28

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Se eliminan los archivos de despliegue en Railway (D-12) o se conservan? → A: Se conservan y se mueven junto a su Dockerfile; el repo nuevo no está conectado a Railway, pero eliminarlos quitaría una capacidad existente sin una spec que lo decida.
- Q: ¿Dónde queda el script de entrenamiento del clasificador mientras no se reescriba (spec 005)? → A: En `mdva/modeling/train.py`, con el mismo comportamiento y rutas resueltas por `mdva/config.py`.
- Q: ¿Dónde queda el script de entrenamiento del regresor de intensidad del routing service? → A: Dentro de `services/routing_api/`, junto al servicio que lo consume, hasta que la spec 009 lo elimine.
- Q: ¿Los dos CSV de SIATA van ambos a `data/raw/`? → A: No. `precipitacion_siata_plano.csv` es el dato crudo → `data/raw/siata/`; `clean_precipitacion_siata_plano.csv` es un derivado hecho por el equipo → `data/interim/siata/`. La spec 003 decide cuál se usa.

## User Scenarios & Testing *(mandatory)*

Los usuarios de esta spec son **quien revisa el portafolio** (reclutador o entrevistador de Ciencia de Datos) y **quien desarrolla** el proyecto. El producto final (la app de viajes) no debe notar ningún cambio.

### User Story 1 - Un revisor entiende el proyecto por su estructura (Priority: P1)

Una persona que abre el repositorio reconoce de inmediato la convención Cookiecutter Data Science v2: datos, modelos, notebooks, reportes, referencias y el paquete de ciencia de datos están en sus lugares estándar, y los servicios y aplicaciones del producto están separados del trabajo de ML.

**Why this priority**: es el primer contacto del revisor con el proyecto; una raíz desordenada (PDFs, manuales, planes de sprint, carpetas con mayúsculas mezcladas) resta credibilidad antes de leer una línea de código.

**Independent Test**: listar la raíz del repositorio y comprobar que coincide con el árbol objetivo del charter §2, sin archivos sueltos fuera de lugar.

**Acceptance Scenarios**:

1. **Given** un clon limpio del repositorio, **When** se lista la raíz, **Then** aparecen solo las carpetas y archivos del árbol objetivo (charter §2) y ningún documento suelto (informes, manuales, PDFs).
2. **Given** el repositorio reorganizado, **When** se busca el notebook de exploración, **Then** está en `notebooks/` con el nombre según la convención `<n>.<m>-<iniciales>-<descripcion>`.
3. **Given** el repositorio reorganizado, **When** se buscan los documentos del curso (informe, manuales, planes de sprint), **Then** están en `docs/` (texto) o `references/` (PDFs).

---

### User Story 2 - El sistema funciona exactamente igual que antes (Priority: P1)

Quien desarrolla levanta el stack completo con el mismo comando de siempre y obtiene los mismos 5 servicios, en los mismos puertos, con los mismos datos persistidos.

**Why this priority**: la constitución (principio I) exige preservar los requisitos del charter §4; una reestructura que rompe el arranque no es aceptable.

**Independent Test**: levantar el stack con el comando documentado y ejecutar el smoke test (health de los 3 backends, registro, login, predicción de lluvia del servicio ML, ruta del routing service).

**Acceptance Scenarios**:

1. **Given** el repositorio reorganizado y el `.env` local existente, **When** se ejecuta el comando de arranque de desarrollo, **Then** los 5 servicios quedan sanos en los puertos 5436, 8081, 8000, 8080 y 8090.
2. **Given** el volumen de base de datos existente, **When** arranca el stack, **Then** los usuarios y viajes previos siguen disponibles (no se reinicializa la base).
3. **Given** el stack levantado, **When** se ejecuta el smoke test, **Then** todas sus verificaciones dan el mismo resultado que antes de la reestructura (incluida la falla conocida de Google, H-19, que se resuelve en specs posteriores).
4. **Given** el repositorio reorganizado, **When** se corren los tests del Backend y el build del Frontend, **Then** dan el mismo resultado que antes (152/153 tests; el que falla requiere una base de pruebas que solo existe en CI).

---

### User Story 3 - El repositorio no carga basura (Priority: P2)

El repositorio no versiona archivos sin uso: respaldos de base de datos obsoletos, configuración personal de IDE, scripts duplicados, código muerto ni datos crudos.

**Why this priority**: reduce ruido y peso; un revisor que encuentra `.idea/` o un respaldo binario de base de datos asume falta de cuidado.

**Independent Test**: comprobar que los archivos marcados para eliminación en el charter §3.1 (salvo los que dependen de specs posteriores) ya no están versionados y que los datos crudos están ignorados por git.

**Acceptance Scenarios**:

1. **Given** el repositorio reorganizado, **When** se listan los archivos versionados, **Then** no aparecen respaldos de base de datos, configuración de IDE, el script de entrenamiento duplicado, el servicio SIATA simulado ni los READMEs duplicados del servicio ML.
2. **Given** los CSV de SIATA en la raíz, **When** se reorganiza, **Then** el crudo queda en `data/raw/siata/`, el derivado en `data/interim/siata/`, y git ignora ambos.

---

### User Story 4 - El despliegue de producción vuelve a construir (Priority: P3)

La configuración de producción construye el Backend con el contexto correcto.

**Why this priority**: hoy `docker-compose.prod.yml` construye el Backend con la raíz del repo como contexto, incompatible con su Dockerfile; está roto antes de esta spec. Se corrige porque la reestructura obliga a tocar esas rutas de todas formas.

**Independent Test**: validar la configuración de producción y construir la imagen del Backend con ella.

**Acceptance Scenarios**:

1. **Given** la configuración de producción, **When** se construye la imagen del Backend, **Then** la construcción termina sin errores.

### Edge Cases

- Los nombres de carpeta cambian de mayúsculas (`Backend` → `apps/backend`) en Windows, que no distingue mayúsculas: el movimiento no debe perder archivos ni historial.
- El nombre del proyecto de Docker Compose debe seguir siendo el mismo, para que los volúmenes existentes (`postgres_data`, `routing_graph_cache`) se reutilicen y no se creen vacíos.
- Contenedores viejos creados desde otra carpeta (copia en OneDrive) no deben interferir: el arranque los recrea desde la carpeta correcta.
- El archivo de exclusiones de Docker del Backend nunca funcionó (le falta el punto inicial); al activarlo no debe excluir archivos que el contenedor necesita para arrancar (p. ej. el perfil `dev`).
- Los modelos de ML pesados (64 MB) se mueven pero siguen versionados hasta que la spec 005 los reemplace; sacarlos ahora rompería el arranque desde un clon limpio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio MUST seguir el árbol objetivo del charter §2 (convención CCDS v2): `data/{raw,interim,processed,external}`, `docs/`, `models/`, `notebooks/`, `references/`, `reports/figures/`, paquete `mdva/`, `services/ml_api/`, `services/routing_api/`, `apps/backend/`, `apps/frontend/`, `db/`, `tests/`.
- **FR-002**: Cada archivo movido MUST conservar su historial en git (movimiento detectable como renombre).
- **FR-003**: El comando de arranque de desarrollo documentado MUST seguir siendo el mismo y levantar los 5 servicios en los mismos puertos (charter RF-01, RF-02, RF-03).
- **FR-004**: El arranque MUST reutilizar los volúmenes de datos existentes (mismo nombre de proyecto de Compose).
- **FR-005**: Ningún comportamiento observable de los servicios (endpoints, respuestas, reglas de negocio del charter §4) MUST cambiar.
- **FR-006**: El paquete `mdva/` MUST existir con un módulo de configuración que sea el único lugar donde se definen las rutas del proyecto (charter E-04); el script de entrenamiento existente MUST resolver sus rutas a través de él en lugar de rutas absolutas o relativas a carpetas externas.
- **FR-007**: Los archivos del charter §3.1 aplicables a esta spec MUST eliminarse o reubicarse: D-02, D-04, D-05, D-07, D-08, D-09, D-10, D-11, D-13. Quedan fuera D-03 (spec 009), D-06 (spec 005) y D-12 (se conserva; ver Clarifications).
- **FR-008**: `data/` y su contenido MUST estar ignorados por git, salvo marcadores de carpeta; el CSV crudo de SIATA MUST quedar en `data/raw/siata/` y el derivado "clean" en `data/interim/siata/`.
- **FR-009**: La CI existente (Backend y Frontend) y el flujo de release MUST apuntar a las nuevas rutas y seguir ejecutando los mismos pasos.
- **FR-010**: La configuración de producción MUST construir el Backend con un contexto compatible con su Dockerfile.
- **FR-011**: La documentación operativa (`README.md`, `CLAUDE.md`) MUST reflejar las nuevas rutas; ninguna instrucción documentada MUST apuntar a una ruta inexistente.
- **FR-012**: Las rutas que usan los scripts de spec-kit y la propia constitución/charter MUST seguir siendo válidas.

### Key Entities

- **Mapa de reubicación**: correspondencia origen → destino de cada archivo o carpeta (charter §3.2), fuente de verdad para verificar FR-001 y FR-002.
- **Servicio del stack**: nombre, puerto host, contexto de construcción, healthcheck; su contrato externo (puerto + health) no cambia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La raíz del repositorio contiene como máximo los elementos del árbol objetivo más los archivos de configuración de herramientas (control de versiones, compose, ignore, licencia, Makefile); 0 documentos sueltos.
- **SC-002**: 100 % de los archivos movidos aparecen como renombres en el historial (ningún archivo movido figura como borrado y recreado), salvo los marcados como "contenido reescrito" en el mapa de reubicación.
- **SC-003**: El smoke test de punta a punta tiene exactamente el mismo resultado antes y después de la reestructura (mismas verificaciones aprobadas y la misma falla conocida H-19).
- **SC-004**: Los tests del Backend dan el mismo resultado (152 de 153) y el build del Frontend termina sin errores.
- **SC-005**: 0 referencias en archivos versionados a rutas que ya no existen (`Data-science/`, `Backend/`, `Frontend/`, `DB/`), salvo en el registro histórico del charter y en documentos del curso preservados tal cual.
- **SC-006**: Los datos de los usuarios en la base de desarrollo existente siguen disponibles después del arranque (mismo número de usuarios antes y después).

## Assumptions

- Se trabaja directo sobre `main`, con un commit por fase y por tarea (decisión del autor del 2026-10-28).
- El routing service se mantiene autocontenido en `services/routing_api/` (no importa `mdva/` todavía); su contexto de construcción sigue siendo su propia carpeta.
- El servicio ML pasa a construirse con la raíz del repo como contexto, porque sus modelos se mueven a `models/` en la raíz (convención CCDS).
- Los documentos del curso (informe técnico, manuales, planes de sprint) se mueven sin editar su contenido; sus rutas internas desactualizadas se aceptan como registro histórico.
- El código del Backend y del Frontend no se modifica: solo cambia su ubicación y la configuración que apunta a ellos.
- La falla de Google (H-19) persiste tras esta spec; se resuelve en las specs 007, 008 y 011.
