# Frontend — MDVA

React 19 + Vite. Mapas con **MapLibre GL** y teselas de OpenStreetMap (el tema oscuro se pinta en el cliente); búsqueda de direcciones con **Nominatim** a través del Backend. No requiere ninguna API key (spec 011).

## Ejecutar

```bash
npm install
npm run dev          # http://localhost:5173 (Backend en VITE_API_URL, por defecto http://localhost:8080)
npm test             # vitest: decodificación de polyline y escala de color del heatmap
npm run lint
npm run build
```

Con el stack completo: `docker compose -f docker-compose.dev.yml up --build` (Frontend en http://localhost:8090).

## Pantallas

| Ruta | Qué muestra |
|---|---|
| `/` | Mapa de la ciudad con la probabilidad de lluvia del modelo (malla 9 × 9, escala fija con leyenda) y pronóstico de 6 h |
| `/planificar` | Búsqueda de origen, destino y paradas (Enter o botón), GPS, toque en el mapa y pines arrastrables |
| `/viaje/:id` | Ruta, alerta de lluvia y alternativa (más seca o más corta) |
| `/viaje/:id/en-ruta` | Navegación con cámara inclinada, rumbo suavizado y orientación del dispositivo |
| `/historial/:idUsuario` | Viajes anteriores |

## Mapa (`src/map/`)

- `MapView.jsx`: crea el mapa y expone `useMap()` a los componentes hijos.
- `geo.js`: decodificación de *encoded polyline* (precisión 1e-5) y cajas.
- `primitives.js`: líneas GeoJSON y marcadores.
- `rainScale.js`: escala de color de probabilidad (cortes en los umbrales 40 % y 70 %) e interpolación bilineal de la malla. El heatmap pinta la probabilidad tal cual: sin re-escalar ni agregar textura.

Teselas configurables con `VITE_TILES_URL` (ver `.env.example`); para tráfico alto, usar un servidor de teselas propio. El tema oscuro invierte el brillo y rota el tono de la misma capa raster (las teselas oscuras de CARTO exigen API key).

La búsqueda de direcciones se dispara al enviar el texto, no por tecla: la [política de Nominatim](https://operations.osmfoundation.org/policies/nominatim/) prohíbe el autocompletado contra su servidor público.
