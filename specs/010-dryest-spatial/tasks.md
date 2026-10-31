---

description: "Task list for 010-dryest-spatial"
---

# Tasks: Ruta `dryest` espacial real

**Tests**: pedidos por la spec (FR-003, SC-001); sin red ni grafo real.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 [P] `services/routing_api/infrastructure/rain_grid.py` (`RainGrid`, `RainGridClient`, `grid_axes`) con `tests/test_rain_grid.py` (25 puntos en 1 + 1 llamadas, caché por caja, grilla incompleta → no disponible, interpolación bilineal y bordes)

## Phase 2: User Story 1 + 2 - Ruta más seca y exposición (Priority: P1/P2) 🎯 MVP

- [X] T002 [US1] [US2] Costo `dryest` por arista y `rain_exposure` en `infrastructure/networkx_routing_service.py`; `dryest_available` y `rain_exposure` en `application/dtos.py`/`use_cases.py`; cableado en `presentation/dependencies.py`; `tests/test_dryest.py` (grilla no uniforme → `dryest` ≠ `fastest` con exposición < 50 %; uniforme → coincide; máximo < 0.10 o sin señal → no se calcula)

## Phase 3: User Story 3 - Alternativa del Backend (Priority: P2)

- [X] T003 [US3] `RoutingApiClient`: preferir la alternativa `dryest`; test en `RoutingApiClientTest`

## Phase 4: Polish

- [X] T004 Stack: una ruta larga (Bello → Envigado) con `dryest_available`, conteo de llamadas, tiempo < 5 s; decisión R-27 en el README del routing service; cerrar la spec

## Dependencies & Execution Order

T001 → T002 → T003 → T004.
