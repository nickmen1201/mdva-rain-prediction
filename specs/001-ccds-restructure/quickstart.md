# Quickstart: validar la reestructuración CCDS v2

## Prerrequisitos

- Docker Desktop corriendo; Python 3.11+; JDK 21; Node 20+.
- `.env` en la raíz y `apps/frontend/.env` (antes `Frontend/.env`) con los valores locales (ver `.env.example`).

## 1. Línea base (antes de mover nada)

```bash
docker compose -f docker-compose.dev.yml up --build -d
python tests/e2e/smoke_stack.py > /tmp/smoke-before.json
psql -h localhost -p 5436 -U postgres -d mdva -tAc "select count(*) from usuarios"   # anotar N
```

## 2. Después de la reestructura

```bash
docker compose -f docker-compose.dev.yml up --build -d
python tests/e2e/smoke_stack.py > /tmp/smoke-after.json
diff /tmp/smoke-before.json /tmp/smoke-after.json        # esperado: sin diferencias de estado
psql -h localhost -p 5436 -U postgres -d mdva -tAc "select count(*) from usuarios"   # esperado: N (+ usuarios de smoke)
```

Resultado esperado del smoke test (igual antes y después): health de los 3 backends OK, registro y login OK, predicción ML OK, ruta del routing service OK, y `planificar` falla con 500 por H-19 (Google sin facturación).

## 3. Builds y tests

```bash
(cd apps/backend && ./gradlew test)            # esperado: 152/153 (falla contextLoads sin BD de CI)
(cd apps/frontend && npm ci && npm run build)  # esperado: build OK
docker compose -f docker-compose.prod.yml --env-file .env.example config -q   # esperado: sin errores
docker build -f apps/backend/Dockerfile apps/backend                          # esperado: OK (US4)
```

## 4. Estructura y limpieza

```bash
ls                                                     # comparar con contracts/repo-layout.md
git log --follow --oneline -- services/ml_api/main.py  # esperado: historial anterior visible
git grep -nE "Data-science/|\bBackend/|\bFrontend/|\bDB/" -- . ':!docs/*' ':!.specify/memory/charter.md' ':!specs/*'
                                                       # esperado: sin resultados
git status --ignored data/                             # esperado: CSV de SIATA ignorados
```
