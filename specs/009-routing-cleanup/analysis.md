# Specification Analysis Report — 009-routing-cleanup

**Fecha**: 2026-10-31 · **Constitución**: v1.0.0

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Constitution | HIGH → resuelto | charter §4 RF-17/RF-22/RF-23 vs FR-010 | Retirar v1 cambia requisitos preservados del charter. | T008 enmienda el charter a 2.0.0 (MAJOR) en el mismo commit que retira v1. |
| A2 | Inconsistency | MEDIUM | charter R-29 ("Open-Meteo o ml_api fallan") vs spec FR-004 | Coinciden; la spec agrega que las señales fallidas no se cachean. | Aceptado (más estricto). |
| A3 | Ambiguity | MEDIUM | FR-005 | Con un factor uniforme, la lluvia no cambia el camino de `fastest`. | Documentado en Clarifications y research R4; la variación espacial es la spec 010. |
| A4 | Coverage | LOW | SC-003 | El rango 6–20 min para ~5 km solo se verifica en el stack. | T009 lo registra. |
| A5 | Underspecification | LOW | FR-007 | El umbral de giro (30°) es una elección. | Documentado en research R6. |

**Coverage Summary**: FR-001 (T004) · FR-002 (T003) · FR-003 (T003) · FR-004 (T003, T006) · FR-005 (T005, T006) · FR-006 (T006) · FR-007 (T006) · FR-008 (T007) · FR-009 (T003, T005, T007) · FR-010 (T008) · FR-011 (T006, T009). Cobertura 11/11.

**Metrics**: 11 FR · 9 tareas · 0 CRITICAL · 0 HIGH abiertos · 2 MEDIUM · 2 LOW.

**Next Actions**: sin CRITICAL; continuar con `implement` tras cerrar la spec 008.
