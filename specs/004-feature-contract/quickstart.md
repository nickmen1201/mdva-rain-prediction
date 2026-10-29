# Quickstart: validar el contrato de features

```bash
uv run pytest tests/test_features.py -v
```

Esperado:
- paridad dataset ↔ registros tipo petición con diferencia máxima 0 (1 000 filas reales si existe `data/processed/rain_hourly.parquet`; sintéticas siempre);
- rechazos con mensaje que nombra el campo: faltante, nulo, fuera de rango, instante sin zona horaria;
- 0° y 360° producen las mismas componentes de viento; 12:00 UTC → hora local 7;
- `docs/features.md` lista las 13 features en el orden del código.

```python
import pandas as pd
from mdva.features import build_features
build_features(pd.DataFrame([{"time_utc": "2026-10-28T20:00:00Z", "temperature_2m": 19.0, "relative_humidity_2m": 85,
    "dew_point_2m": 16.4, "cloud_cover": 90, "wind_speed_10m": 2.0, "wind_direction_10m": 180,
    "pressure_msl": 1013, "precipitation": 0.4, "cape": 300}]))
```

## Verificación registrada (2026-10-28)

- Paridad con 1 000 filas reales del dataset (`random_state=0`) y 500 sintéticas: diferencia máxima **0.0**.
- 8 casos de entrada inválida rechazados nombrando el campo (faltante, nulo, fuera de rango ×2, no numérico, sin zona horaria, no ISO 8601, instante nulo).
- `build_features` sobre las 455 832 filas del dataset: 0.08 s.
- `docs/features.md` coincide con `FEATURES` (13 features, mismo orden).
