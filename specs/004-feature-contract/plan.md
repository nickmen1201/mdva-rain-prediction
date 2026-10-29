# Implementation Plan: Contrato y módulo único de features

**Branch**: `004-feature-contract` (trabajo directo en `main`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-feature-contract/spec.md`

## Summary

`mdva/features.py` define el contrato de entradas crudas (instante UTC + 9 variables pronosticadas, con los rangos de `mdva.data_contract`), lo valida y produce 13 features en orden fijo y versionado (`FEATURE_CONTRACT_VERSION = "1.0.0"`): identidades, depresión del punto de rocío, componentes del viento, `log1p` de precipitación y CAPE, y codificación cíclica de hora y mes locales de Bogotá. Pruebas de paridad (dataset vs. registros tipo petición) y de sincronía con `docs/features.md`.

## Technical Context

**Language/Version**: Python 3.11 (paquete `mdva`)

**Primary Dependencies**: pandas, numpy (ya presentes); `zoneinfo` de la stdlib. Sin dependencias nuevas.

**Storage**: N/A (sin estado)

**Testing**: pytest (sintético en CI; paridad con el dataset real si existe `data/processed/rain_hourly.parquet`)

**Target Platform**: paquete `mdva`, usado por el entrenamiento (spec 005) y el ML API (spec 006)

**Project Type**: librería interna

**Performance Goals**: 456 k filas en < 2 s (vectorizado)

**Constraints**: sin estado; mismas features en entrenamiento y en inferencia

**Scale/Scope**: 1 módulo, 13 features

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| I. Intención cuesta abajo | Eliminación de la feature de lag y cambio de `hora`/`mes` a `time_utc` decididos en la spec. | ✅ |
| IV. Contract-first | [contracts/features.v1.md](contracts/features.v1.md) antes del código; cambio clasificado como rompiente frente al modelo anterior. | ✅ |
| VI. Paridad train/serve | Un solo módulo; prueba de paridad; ninguna feature sin equivalente en producción. | ✅ |
| VII. Sin datos fabricados | No se rellenan features faltantes; se rechazan. | ✅ |
| Timestamps UTC | Entrada en UTC con zona; hora local solo como feature. | ✅ |

**Post-design re-check**: sin violaciones.

## Project Structure

```text
specs/004-feature-contract/{plan.md, research.md, quickstart.md, tasks.md, contracts/features.v1.md}
mdva/features.py
docs/features.md
tests/test_features.py
```

No hay `data-model.md` aparte: la única entidad (contrato de features) está en el contrato.

**Structure Decision**: módulo `features.py` de la plantilla CCDS v2.

## Complexity Tracking

Sin violaciones.
