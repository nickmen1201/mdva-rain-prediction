# Implementation Plan: Frontend sin Google — MapLibre, teselas OSM y búsqueda con Nominatim

**Branch**: `011-frontend-maplibre` (trabajo directo en `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

## Summary

Un módulo `src/map/` reemplaza a `@vis.gl/react-google-maps`: `MapView` (MapLibre GL + teselas raster OSM con tema oscuro pintado en el cliente, contexto con `useMap()` para no reescribir los componentes hijos), `geo.js` (decodificación de *encoded polyline* y cajas), `primitives.js` (líneas GeoJSON y marcadores circulares) y `rainScale.js` (escala de color fija y raster del heatmap). El heatmap deja deck.gl y usa una fuente `image` nativa de MapLibre. `PlaceSearch` busca direcciones al enviar el texto (`/api/geocoding/search`) y el toque en el mapa usa `/api/geocoding/reverse`. La cámara de navegación usa `easeTo({pitch, bearing})`.

## Technical Context

**Language/Version**: React 19, Vite 5, Node 20.

**Primary Dependencies**: **agrega** `maplibre-gl` 5.24.0 (renderizador de mapas abierto, sin key; sustituto directo de Google Maps JS) y, solo en desarrollo, `vitest` 3.2.7 + `jsdom` (pruebas unitarias de las utilidades puras: decodificación y escala de color; no había runner). **Quita** `@vis.gl/react-google-maps`, `@deck.gl/google-maps` y `@deck.gl/layers` (el raster del heatmap se dibuja con una fuente de imagen de MapLibre). Versiones exactas en `package-lock.json`.

**Testing**: `npm test` (vitest), `npm run lint`, `npm run build`; verificación visual con navegador automatizado sobre el stack.

**Constraints**: rutas RF-21, tema claro/oscuro, mobile-first y navegación 3D intactos.

## Constitution Check

| Principio | Cómo se cumple | Estado |
|---|---|---|
| II. Sin APIs de pago | MapLibre + OSM + Nominatim vía Backend: ninguna key. | ✅ |
| VII. Sin datos fabricados | El heatmap ya no re-escala ni agrega ruido (H-35) y descarta puntos sin probabilidad (antes `?? 0`). | ✅ |
| Dependencias justificadas | Una de runtime agregada, tres quitadas; vitest solo en desarrollo. | ✅ |
| Calidad | ESLint + vitest + build en `ci-frontend.yml`. | ✅ |

## Project Structure

```text
apps/frontend/
├── src/map/MapView.jsx, mapStyle.js, geo.js, primitives.js, rainScale.js (+ *.test.js)   # nuevo
├── src/components/PlaceSearch.jsx                  # nuevo
├── src/components/WeatherHeatmapLayer.jsx          # fuente image + RainLegend
├── src/components/MapaRuta.jsx                     # polyline y marcadores MapLibre
├── src/pages/{MapaCiudad,PlanificarViaje,EnRuta,ResultadoViaje}.jsx
├── src/hooks/{useNavigationCamera,useWeatherGrid}.js
├── src/App.jsx, src/api/client.js, src/index.css
├── package.json, package-lock.json, vite.config.js, .env.example, Dockerfile
.github/workflows/ci-frontend.yml                  # + npm test
```

## Complexity Tracking

Sin violaciones.
