# Feature Specification: Documentación de portafolio

**Feature Branch**: `013-portfolio-docs` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Implemented (2026-10-31)

**Input**: "Spec 013 (charter R-42–R-44, P8): README orientado a ciencia de datos con resultados generados desde `metrics.json`, autoría clara, sin artefactos de herramientas en el repositorio y documentación sincronizada con el código."

## Clarifications

### Session 2026-10-31

- Q: ¿Qué archivos de herramientas se retiran del control de versiones? → A: `CLAUDE.md` y la configuración local de spec-kit (`.specify/` salvo la constitución y el charter, que son documentos del proyecto). Quedan en `.gitignore`.
- Q: ¿Cómo se evita que el README se desincronice de las métricas? → A: La tabla de resultados la genera `mdva/readme.py` desde `metrics.json` entre marcadores, y un test compara el README versionado con lo que se generaría (R-44).
- Q: ¿Se agrega una licencia? → A: No en esta spec: es una decisión de los cuatro autores del proyecto original.

## Requirements

- **FR-001**: El README MUST cubrir problema → datos → etiqueta → features → validación → resultados vs baselines (generados) → calibración y umbrales → producto → reproducción → limitaciones → autoría (R-42, P8).
- **FR-002**: Ninguna cifra de desempeño del README o de la model card MUST escribirse a mano (R-44); un test lo verifica.
- **FR-003**: El repositorio MUST NOT versionar archivos de configuración de asistentes ni de herramientas locales.
- **FR-004**: El charter MUST corregir lo que la implementación mostró inexacto: autocompletado de Nominatim (R-35b/R-35c) y RF-11 (regla que nunca existió).

## Success Criteria

- **SC-001**: `tests/test_readme.py` y `tests/test_model_card.py` en verde.
- **SC-002**: `git ls-files | grep -iE "claude|\.specify/(scripts|templates|integrations)"` sin resultados.
