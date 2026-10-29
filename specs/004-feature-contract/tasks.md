---

description: "Task list for 004-feature-contract"
---

# Tasks: Contrato y módulo único de features

**Input**: Design documents from `/specs/004-feature-contract/`

**Tests**: pedidos por la spec (FR-008, FR-009, SC-001, SC-002).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 2 - Entradas inválidas se rechazan (Priority: P1)

- [X] T001 [US2] `RAW_INPUTS`, `FeatureInputError` y `validate_inputs` en `mdva/features.py` (rangos de `mdva.data_contract`, instante con zona → UTC) con tests de rechazo en `tests/test_features.py`

## Phase 2: User Story 1 - Mismas features en entrenamiento y producción (Priority: P1) 🎯 MVP

- [X] T002 [US1] `FEATURES`, `FEATURE_CONTRACT_VERSION` y `build_features` en `mdva/features.py` (transformaciones del contrato) con tests de transformaciones en `tests/test_features.py`
- [X] T003 [US1] Prueba de paridad dataset ↔ registros tipo petición (sintética + real si existe el dataset) en `tests/test_features.py`; registrar el resultado con el dataset real en `specs/004-feature-contract/quickstart.md`

## Phase 3: User Story 3 - Features documentadas (Priority: P2)

- [X] T004 [US3] `docs/features.md` (feature card: origen, unidad, transformación, motivo; variables descartadas) y test de sincronía con `FEATURES`

## Phase 4: Polish

- [X] T005 Verificar SC-001…SC-004 y cerrar la spec

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 (mismo módulo y mismo archivo de tests).
