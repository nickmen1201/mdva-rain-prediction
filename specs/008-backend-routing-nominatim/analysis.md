# Specification Analysis Report — 008-backend-routing-nominatim

**Fecha**: 2026-10-31 · **Constitución**: v1.0.0

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Inconsistency | MEDIUM | charter R-35b/R-35c ("autocompletado vía Nominatim") vs spec Clarifications | La política de Nominatim prohíbe el autocompletado por tecla. | Búsqueda al enviar (spec), adoptada por el Frontend en la 011; corregir la redacción del charter en la spec 013. |
| A2 | Coverage | MEDIUM | FR-002 vs routing service | El routing service sigue calculando y devolviendo campos de lluvia propios. | Aceptado: el Backend no los lee (T002 lo prueba); se eliminan en la spec 009. |
| A3 | Underspecification | LOW | FR-005 | La línea recta puede elegir un orden subóptimo en red. | Documentado en research R3; se acepta como heurística. |
| A4 | Coverage | LOW | SC-005 | El tiempo de respuesta solo se mide en el smoke test. | T009 lo registra. |

**Coverage Summary**: FR-001 (T002, T004) · FR-002 (T004) · FR-003 (T001, T004) · FR-004 (T002) · FR-005 (T003, T004) · FR-006 (T002, T004) · FR-007 (T007) · FR-008 (T006) · FR-009 (T002, T008) · FR-010 (T005, T009) · FR-011 (T004, T009). Cobertura 11/11.

**Metrics**: 11 FR · 9 tareas · 0 CRITICAL · 0 HIGH · 2 MEDIUM · 2 LOW.

**Next Actions**: sin CRITICAL; continuar con `implement`.
