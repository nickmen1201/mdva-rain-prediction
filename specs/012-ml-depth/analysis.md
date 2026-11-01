# Specification Analysis Report — 012-ml-depth

**Fecha**: 2026-10-31 · **Constitución**: v1.0.0

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Constitution | HIGH → resuelto | FR-010 vs constitución IV | El contrato 1.1.0 agrega entradas obligatorias al ML API (cambio rompiente). | Contrato 2.1.0 escrito antes del código; los dos consumidores se actualizan en la misma spec; los campos extra eran ignorados por 2.0.0, así que el orden de despliegue no rompe nada (Complexity Tracking del plan). |
| A2 | Ambiguity | MEDIUM | SC-001 | "Misma configuración elegida" entre corridas depende del determinismo de HGB con semilla fija. | La búsqueda usa semilla fija y sin *early stopping*; la corrida de punta a punta sintética de `tests/test_predict.py` verifica determinismo del entrenamiento. |
| A3 | Coverage | MEDIUM | SC-003 | El ECE < 0.03 se cumple en desarrollo pero puede no cumplirse en 2025/2026 por cambio de régimen. | La spec ya lo prevé ("o la model card explica por qué no"); documentado en model card y README. |
| A4 | Underspecification | LOW | FR-003 | El proxy de complejidad para la regla de 1 EE es una elección. | Documentado en research R3/R4. |

**Coverage Summary**: FR-001 (T005) · FR-002 (T002) · FR-003 (T003) · FR-004 (T004, T005) · FR-005 (T005) · FR-006 (T004, T005) · FR-007 (T004, T005) · FR-008 (T001, T007) · FR-009 (T005, T007) · FR-010 (T006, T008) · FR-011 (T009) · FR-012 (T007). Cobertura 12/12.

**Metrics**: 12 FR · 10 tareas · 0 CRITICAL · 0 HIGH abiertos · 2 MEDIUM · 1 LOW.
