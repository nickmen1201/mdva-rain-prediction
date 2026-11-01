---

description: "Task list for 011-frontend-maplibre"
---

# Tasks: Frontend sin Google

**Tests**: pedidos por la spec (FR-009) para las utilidades puras; el resto se verifica en el stack con navegador.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [X] T001 Dependencias: `maplibre-gl` (runtime), `vitest` + `jsdom` (desarrollo); quitar `@vis.gl/react-google-maps`, `@deck.gl/*`; `npm test` en `package.json` y en `.github/workflows/ci-frontend.yml`
- [X] T002 [P] `src/map/geo.js` y `src/map/rainScale.js` con `geo.test.js` y `rainScale.test.js`
- [X] T003 [P] `src/map/MapView.jsx`, `mapStyle.js`, `primitives.js`

## Phase 2: User Story 1 - Mapa de la ciudad y heatmap (Priority: P1) 🎯 MVP

- [X] T004 [US1] `WeatherHeatmapLayer.jsx` (fuente image, `RainLegend`), `useWeatherGrid.js` sin rellenos, `MapaCiudad.jsx`, `App.jsx` sin `APIProvider`

## Phase 3: User Story 2 + 3 - Planificar y resultado (Priority: P1/P2)

- [X] T005 [US2] `PlaceSearch.jsx`, `api/client.js` (`searchPlaces`, `reversePlace`), `PlanificarViaje.jsx` (búsqueda, toque, pines arrastrables)
- [X] T006 [US3] `MapaRuta.jsx` y rótulo de la alternativa en `ResultadoViaje.jsx`

## Phase 4: User Story 4 - Navegación (Priority: P2)

- [X] T007 [US4] `EnRuta.jsx` (ruta, recorrido, marcadores, flecha GPS con rumbo) y `useNavigationCamera.js` (`easeTo` con `pitch`/`bearing`)

## Phase 5: Polish

- [X] T008 `.env.example`, `Dockerfile` y README del Frontend sin Google; stack reconstruido; recorrido login → mapa → planificar (búsqueda) → resultado → en ruta con navegador automatizado y capturas; cerrar la spec

## Dependencies & Execution Order

T001 → (T002, T003) → T004 → T005 → T006 → T007 → T008.
