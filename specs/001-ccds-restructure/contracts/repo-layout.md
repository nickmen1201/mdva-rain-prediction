# Contract: Mapa de reubicación del repositorio

Fuente de verdad para FR-001, FR-002 y FR-007. Cada fila se verifica como renombre en git (`git log --follow`) o como eliminación.

## Movimientos

| Origen | Destino |
|---|---|
| `Data-science/main.py` | `services/ml_api/main.py` |
| `Data-science/Dockerfile` | `services/ml_api/Dockerfile` |
| `Data-science/requirements.txt` | `services/ml_api/requirements.txt` |
| `Data-science/railway.toml` | `services/ml_api/railway.toml` |
| `Data-science/models/random_forest.pkl` | `models/random_forest.pkl` |
| `Data-science/models/regresion_logistica.pkl` | `models/regresion_logistica.pkl` |
| `Data-science/train_models.py` | `mdva/modeling/train.py` |
| `Data-science/notebooks/MDVA_analisis_espacial_prototipo.ipynb` | `notebooks/1.0-nm-analisis-espacial-siata-vs-openmeteo.ipynb` |
| `Data-science/enrutamiento_ambiental/**` | `services/routing_api/**` |
| `Backend/**` | `apps/backend/**` |
| `Frontend/**` | `apps/frontend/**` |
| `DB/init-docker.sql` | `db/init-docker.sql` |
| `DB/Resources/{barrios,comunas,municipios}.csv` | `db/seeds/` |
| `DB/Resources/webscraper_municipios.py` | `db/scripts/webscraper_municipios.py` |
| `Informe_Tecnico.md` | `docs/informe-tecnico.md` |
| `Manual_Pruebas.md` | `docs/manual-pruebas.md` |
| `Manual_Usuario.md` | `docs/manual-usuario.md` |
| `Backend/MDVA_Documentacion_Sprint3.md` | `docs/sprints/sprint-3-documentacion.md` |
| `Backend/TEST.md` | `docs/backend-tests.md` |
| `implementationplans/MDVA_Heatmap_Navegacion_Dinamica_Sprints.md` | `docs/sprints/heatmap-navegacion-dinamica.md` |
| `implementationplans/MDVA_Sprint5_Implementation_Plan.md` | `docs/sprints/sprint-5-plan.md` |
| `Informe_Proyecto_MVA (1).pdf` | `references/informe-proyecto-mva.pdf` |
| `Backend/wiki/GENERAL.pdf` | `references/wiki-general.pdf` |
| `Backend/dockerignore` | `apps/backend/.dockerignore` (contenido reescrito, R6) |
| `.github/workflows/ci.yml` | `.github/workflows/ci-backend.yml` |

## Archivos no versionados

| Origen | Destino |
|---|---|
| `precipitacion_siata_plano.csv` | `data/raw/siata/precipitacion_siata_plano.csv` |
| `clean_precipitacion_siata_plano.csv` | `data/interim/siata/clean_precipitacion_siata_plano.csv` |

## Eliminaciones

| Archivo | Ítem del charter |
|---|---|
| `Data-science/enrutamiento_ambiental/scripts/train_rain_model.py` | D-02 |
| `Data-science/enrutamiento_ambiental/infrastructure/siata_live_service.py` | D-04 |
| `Data-science/README.md`, `Data-science/models/README.md` | D-05 (se reemplazan por `services/ml_api/README.md`) |
| `DB/TIC1DB.sql`, `DB/TIC1DB.backup` | D-07 |
| `Backend/.idea/**`, `Backend/.claude/**`, `.vscode/settings.json` | D-08 (se sacan del índice) |
| `CONTEXT.md` | D-13 |
| `Data-science/.gitignore` | se fusiona en el `.gitignore` raíz |

## Archivos nuevos

| Archivo | Propósito |
|---|---|
| `mdva/__init__.py`, `mdva/config.py`, `mdva/modeling/__init__.py` | Paquete CCDS v2 y rutas únicas (FR-006) |
| `data/{raw,interim,processed,external}/.gitkeep`, `reports/figures/.gitkeep`, `tests/e2e/smoke_stack.py` | Estructura CCDS y smoke test (R11) |
| `.dockerignore` (raíz) | Lista de permitidos para el build del servicio ML (R3) |
| `services/ml_api/README.md` | Reemplaza los READMEs duplicados (D-05) |

## Sin cambios

`apps/backend/src/main/generated-jooq/` sigue versionado; `.specify/` y `specs/` no se mueven.
