# Quickstart: validar el ML API v2

```bash
uv run --project services/ml_api pytest services/ml_api/tests     # contrato, v2, RF-17 y caracterización v1
make up && make smoke                                              # incluye ml_v2_health, ml_v2_predict, ml_v2_batch_81
curl -s localhost:8081/v2/health
```

## Verificación registrada (2026-10-28)

- 62 tests del servicio en verde: contrato válido (OpenAPI 3.1) y coincidente con el servicio (rutas, métodos, campos requeridos y de salida, rangos), tabla RF-17 en la función pura y en v2, Problem Details en entradas inválidas y en errores internos (sin detalles internos), arranque fallido con un modelo inexistente, y los 29 tests de caracterización de v1.
- Contenedor reconstruido: `/v2/health` → `ready: true`, `rain_classifier` 1.0.0, calibración `none`; lote de 81 registros en menos de 1 s.
- Smoke test: todas las verificaciones de la línea base idénticas + las 3 nuevas de v2 en verde.
