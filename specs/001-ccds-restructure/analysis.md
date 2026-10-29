# Specification Analysis Report — 001-ccds-restructure

**Fecha**: 2026-10-28 · **Artefactos**: spec.md, plan.md, tasks.md, research.md, contracts/, quickstart.md · **Constitución**: v1.0.0

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Inconsistency | MEDIUM | spec.md SC-002; contracts/repo-layout.md (fila `Backend/dockerignore`) | SC-002 exige que el 100 % de los movidos se detecten como renombre, pero el `.dockerignore` del Backend se reescribe por completo (R6) y git no lo detectará como renombre. | Excluir de SC-002 los archivos marcados como "contenido reescrito" en el contrato. **Aplicado.** |
| A2 | Coverage gap | LOW | spec.md FR-012; tasks.md | Ninguna tarea verifica que los scripts de spec-kit sigan resolviendo rutas. | Agregar a T016 la ejecución de `check-prerequisites.ps1 -PathsOnly`. **Aplicado.** |
| A3 | Underspecification | LOW | tasks.md T008, T009 | Mover y editar en el mismo commit puede impedir la detección de renombre si la edición es grande. | Mantener las ediciones de `main.py` y `train.py` mínimas (solo rutas); verificar con `git log --follow` en T016. Sin cambio de artefactos. |
| A4 | Constitution alignment | — | plan.md Constitution Check | Principio IV (tests de contrato contra el código en ejecución): el smoke test valida puertos y health de `contracts/stack-services.md`. | Sin acción. |

**Coverage Summary**

| Requirement | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 estructura CCDS | Sí | T004, T005–T011 | |
| FR-002 historial | Sí | T005–T011, T016 | ver A1, A3 |
| FR-003 mismo arranque y puertos | Sí | T014 | |
| FR-004 volúmenes reutilizados | Sí | T003, T014 | |
| FR-005 sin cambios observables | Sí | T001, T002, T014 | |
| FR-006 `mdva/config.py` | Sí | T009 | |
| FR-007 limpieza | Sí | T005 (D-09), T008 (D-05), T011 (D-10, D-11), T012 | |
| FR-008 datos ignorados | Sí | T004 | |
| FR-009 CI y release | Sí | T005, T006 | |
| FR-010 prod construye | Sí | T013 | |
| FR-011 docs operativas | Sí | T015 | |
| FR-012 rutas spec-kit | Sí | T016 | ver A2 |

**Constitution Alignment Issues**: ninguno.

**Unmapped Tasks**: ninguna (T001–T002 sirven a FR-005/US2).

**Metrics**: 12 requisitos funcionales · 16 tareas · cobertura 100 % · 0 CRITICAL · 0 HIGH · 1 MEDIUM · 2 LOW.

**Next Actions**: sin hallazgos CRITICAL; se puede pasar a `implement`. A1 y A2 corregidos en los artefactos.
