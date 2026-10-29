# Quickstart: validar tooling Python, calidad y CI

## Entornos y calidad

```bash
make requirements   # o los comandos equivalentes de contracts/developer-commands.md
make lint
make test
make secrets
```

Esperado: lint sin hallazgos, todos los tests en verde y `no leaks found`.

## Prueba negativa de lint (no se commitea)

```bash
echo "import os" > mdva/_tmp_lint.py && uv run ruff check mdva/_tmp_lint.py; rm mdva/_tmp_lint.py
```

Esperado: `F401 'os' imported but unused`, código de salida 1.

## Prueba negativa de secretos (no se commitea)

```bash
mkdir -p /tmp/gl && printf 'GOOGLE_KEY=AIza%s\n' "SyD-ficticia-0123456789abcdefghijklmnop" > /tmp/gl/leak.env
docker run --rm -v /tmp/gl:/scan ghcr.io/gitleaks/gitleaks:v8.30.1 dir /scan
```

Esperado: `leaks found: 1` (regla `gcp-api-key`).

## Imágenes y comportamiento

```bash
make up
docker exec mdva-ml pip freeze        # comparar con el freeze del 2026-10-28
docker exec mdva-routing pip freeze
make smoke                            # comparar con la línea base de la spec 001
```

Esperado: mismas versiones de las librerías principales y smoke test idéntico.

## Verificación registrada de US1 (2026-10-28)

- `services/ml_api`: los 22 paquetes instalados en la imagen reconstruida desde `uv.lock` son idénticos (nombre y versión) al `pip freeze` del contenedor anterior.
- `services/routing_api`: los 76 paquetes son idénticos (antes sin ninguna versión fijada).
- Se excluyen de la comparación `pip`, `setuptools`, `wheel` y `packaging`, que vienen con la imagen base de Python, y `colorama` (solo Windows).
- Smoke test: idéntico a la línea base de la spec 001.

## Verificación final registrada (2026-10-28)

- `make clean` (equivalente) sin errores; `ruff check` y `ruff format --check` sin hallazgos en todo el repo.
- Tests: raíz 36 · `services/ml_api` 29 · `services/routing_api` 17, todos en verde y sin red.
- `gitleaks` sobre la rama actual: `no leaks found`; prueba negativa con credencial ficticia: `leaks found: 1`.
- Smoke test tras reconstruir las imágenes con el código formateado: idéntico a la línea base de la spec 001.
- CI de GitHub: verde en todos los commits subidos hasta el cierre; los workflows nuevos (`ci-python`, `ci-frontend`, `ci-secrets`) se verifican al llegar sus commits.
