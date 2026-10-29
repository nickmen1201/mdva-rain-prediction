# Research: Reestructuración Cookiecutter Data Science v2

Fase 0 del plan. Cada decisión resuelve una incógnita del Technical Context.

## R1. Reutilizar los volúmenes existentes de Docker Compose

- **Decision**: declarar `name: monitoreo-de-variables-ambientales` en la raíz de `docker-compose.dev.yml` y `docker-compose.prod.yml`.
- **Rationale**: hoy el nombre del proyecto sale del nombre de la carpeta. Si alguien clona con otro nombre (p. ej. `mdva-rain-prediction`), Compose crearía volúmenes vacíos y perdería la base de datos y el grafo OSM cacheado (FR-004, SC-006). Fijarlo explícitamente vuelve el comportamiento independiente de la carpeta y coincide con el nombre actual, así que los volúmenes existentes se reutilizan.
- **Alternatives considered**: variable `COMPOSE_PROJECT_NAME` en `.env` (depende de un archivo local no versionado); volúmenes `external: true` (obliga a crearlos a mano en un clon limpio).

## R2. Renombres que solo cambian mayúsculas en Windows

- **Decision**: `DB/` → `db/` se hace en dos pasos (`git mv DB db_tmp` y `git mv db_tmp db`). El resto de movimientos cambian la ruta completa (`Backend/` → `apps/backend/`) y no tienen el problema.
- **Rationale**: NTFS no distingue mayúsculas; `git mv DB db` falla o deja el índice inconsistente. El paso intermedio preserva la detección de renombre (FR-002).
- **Alternatives considered**: `core.ignorecase=false` (riesgoso en Windows, puede duplicar entradas).

## R3. Contexto de construcción del servicio ML

- **Decision**: el servicio ML se construye con la **raíz del repo** como contexto y `services/ml_api/Dockerfile`; un `.dockerignore` en la raíz deja entrar solo `services/ml_api/` y `models/` (lista de permitidos).
- **Rationale**: en CCDS v2 los modelos viven en `models/` en la raíz, fuera de la carpeta del servicio. Una lista de permitidos evita enviar `data/`, `apps/`, `node_modules/` o `.git/` al daemon.
- **Alternatives considered**: copiar los modelos dentro de `services/ml_api/` (rompe la convención y duplica artefactos de 64 MB); symlinks (no funcionan como contexto de build en Windows).

## R4. Ruta de los modelos en el servicio ML

- **Decision**: `main.py` lee la carpeta de modelos de la variable `MDVA_MODELS_DIR`; si no está definida, usa `models/` en la raíz del repo (dos niveles arriba de `services/ml_api/`). El Dockerfile define `MDVA_MODELS_DIR=/app/models`.
- **Rationale**: es el cambio mínimo para que el servicio funcione igual en contenedor y en local tras el movimiento (FR-005). El servicio todavía no importa el paquete `mdva` (eso llega con la spec 006).
- **Alternatives considered**: importar `mdva.config` desde el servicio ya (obliga a instalar el paquete en la imagen, alcance de la spec 006).

## R5. Rutas del script de entrenamiento

- **Decision**: `mdva/config.py` define `PROJ_ROOT`, `DATA_DIR`, `RAW_DATA_DIR`, `INTERIM_DATA_DIR`, `PROCESSED_DATA_DIR`, `EXTERNAL_DATA_DIR`, `MODELS_DIR`, `REPORTS_DIR`, `FIGURES_DIR` con `pathlib`, al estilo de la plantilla CCDS v2. `mdva/modeling/train.py` (el antiguo `train_models.py`) usa `MODELS_DIR` y `RAW_DATA_DIR / "siata"`, y se elimina la ruta absoluta a la máquina de un compañero.
- **Rationale**: cumple FR-006 y la regla E-04 del charter. El script sigue sin poder correr con los datos actuales (formato distinto, H-20), igual que antes de esta spec; se reescribe en la spec 005.
- **Alternatives considered**: dejar el script fuera del paquete hasta la spec 005 (deja la ruta absoluta en el repo un tiempo más). La plantilla CCDS v2 usa `python-dotenv` y `loguru` en `config.py`; se difieren a la spec 002, donde se fijan las dependencias.

## R6. `.dockerignore` del Backend

- **Decision**: reemplazar `Backend/dockerignore` (sin punto, nunca efectivo) por `apps/backend/.dockerignore` con rutas relativas al contexto del Backend: `.gradle/`, `build/`, `bin/`, `out/`, archivos de IDE, `.env*`, `wiki/`. **No** excluye `application-dev.yml`.
- **Rationale**: la imagen arranca con `SPRING_PROFILES_ACTIVE=dev`; el perfil dev ya no tiene secretos (los toma de variables de entorno desde el commit `a47c3c5`), así que excluirlo cambiaría el comportamiento (logging, config de dev) sin ganar seguridad.
- **Alternatives considered**: renombrar el archivo tal cual (sus patrones `Backend/...` no aplican a un contexto `Backend/`, y excluiría el perfil dev).

## R7. Compose de producción roto

- **Decision**: en `docker-compose.prod.yml` el Backend usa `context: ./apps/backend` y `dockerfile: Dockerfile`, igual que en dev.
- **Rationale**: el Dockerfile copia `gradlew`, `gradle/` y `src/` relativos a la carpeta del Backend; con la raíz como contexto la construcción falla (US4, FR-010).
- **Alternatives considered**: adaptar el Dockerfile a contexto raíz (cambia el build de dev y de Railway).

## R8. Railway

- **Decision**: cada `railway.toml` se mueve junto a su Dockerfile. El del servicio ML apunta a `services/ml_api/Dockerfile`, porque su contexto pasa a ser la raíz.
- **Rationale**: clarificación de la spec (se conserva la capacidad de despliegue).

## R9. Documentos del curso y archivos sueltos

- **Decision**:
  - `Informe_Tecnico.md`, `Manual_Pruebas.md` y `Manual_Usuario.md` → `docs/`, con nombres en kebab-case (`informe-tecnico.md`, …).
  - `Backend/MDVA_Documentacion_Sprint3.md` → `docs/sprints/sprint-3-documentacion.md`; `Backend/TEST.md` → `docs/backend-tests.md`.
  - `implementationplans/*` → `docs/sprints/`.
  - `Informe_Proyecto_MVA (1).pdf` → `references/informe-proyecto-mva.pdf`; `Backend/wiki/GENERAL.pdf` → `references/wiki-general.pdf`.
- **Rationale**: CCDS v2 separa la documentación del proyecto (`docs/`) del material de referencia (`references/`); los nombres sin espacios ni paréntesis evitan comillas en cada comando.
- **Alternatives considered**: borrar los documentos del curso (se pierde contexto útil para el revisor del portafolio).

## R10. Licencia

- **Decision**: no se agrega `LICENSE` en esta spec.
- **Rationale**: el código tiene 4 autores; elegir la licencia es decisión del dueño (y probablemente del equipo). Se registra como pendiente para la spec 012.

## R11. Smoke test reproducible

- **Decision**: script en `tests/e2e/smoke_stack.py` (solo stdlib de Python) que verifica health de los 3 backends, registro y login, una predicción del servicio ML, una ruta del routing service y el intento de planificar un viaje; imprime un JSON con el estado de cada verificación. Se corre antes y después para comparar (SC-003).
- **Rationale**: la verificación de punta a punta se va a repetir en cada spec que toque servicios (gate de la constitución); un script evita depender de pasos manuales.
- **Alternatives considered**: comandos `curl` sueltos en el quickstart (no comparables entre corridas); Playwright (sobredimensionado para esta spec).
