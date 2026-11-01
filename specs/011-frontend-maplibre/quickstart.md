# Quickstart: validar el Frontend sin Google

## 1. Calidad

```bash
cd apps/frontend && npm ci && npm test && npm run lint && npm run build
grep -rn "google" src | grep -v fonts.googleapis   # sin resultados
```

## 2. Recorrido en el stack (sin ninguna API key)

```bash
make up   # Frontend en http://localhost:8090
```

1. Registrarse e iniciar sesión → `/`: mapa con teselas, atribución de OSM, heatmap y su leyenda (0–100 %, cortes en 40 % y 70 %).
2. `/planificar`: buscar "Parque Explora" (Enter) y elegir el resultado; tocar el mapa para el destino; planificar.
3. `/viaje/:id`: ruta dibujada con marcadores; si hay alternativa, el botón dice "más seca" o "más corta".
4. "En ruta": la cámara se inclina 60° y sigue el rumbo; arrastrar el mapa la libera y "centrar" la recupera.

## Verificación registrada (2026-10-31)

- **SC-001** ✅ 0 referencias a Google Maps en `apps/frontend` (solo Google Fonts); dependencias `@vis.gl/react-google-maps` y `@deck.gl/*` retiradas.
- **SC-002** ✅ `make ui-smoke` (Chromium headless, stack sin keys): mapa con teselas OSM, atribución y leyenda; búsqueda "Parque Explora" → "Estadio Atanasio Girardot" con Enter; resultado con ruta y 2 marcadores; navegación con pasos por vía ("Sal por Calle 73…"), 0 errores de consola. Capturas en `reports/figures/ui/`.
- **SC-003** ✅ `npm test` (7), `npm run lint` y `npm run build` en verde; MapLibre en su propio chunk.
- Hallazgos al probar con navegador, corregidos: (1) el contenedor nginx no hacía proxy de `/api` y `/auth` hacia el Backend (las llamadas devolvían `index.html` o 405); (2) las teselas oscuras de CARTO exigen API key → tema oscuro pintado en el cliente sobre OSM; (3) abrir la navegación por enlace directo fallaba al no tener destino (guarda agregada).
