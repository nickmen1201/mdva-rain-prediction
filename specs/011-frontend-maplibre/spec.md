# Feature Specification: Frontend sin Google — MapLibre, teselas OSM y búsqueda con Nominatim

**Feature Branch**: `011-frontend-maplibre` (trabajo directo en `main`)

**Created**: 2026-10-31

**Status**: Implemented (2026-10-31)

**Input**: User description: "Spec 011 (charter R-35c, H-19): el Frontend reemplaza Google Maps JS + Places por MapLibre GL con teselas OSM y búsqueda de direcciones vía Backend (Nominatim). Se preservan heatmap, polyline, navegación con cámara inclinada y orientación del dispositivo."

## Clarifications

### Session 2026-10-31

Respondidas por el agente con la opción más conservadora (constitución, "Flujo de trabajo y quality gates").

- Q: ¿Autocompletado mientras se escribe? → A: No: la política de Nominatim lo prohíbe (spec 008). Se busca al presionar Enter o el botón de búsqueda; se muestran hasta 5 resultados para elegir. Tocar el mapa sigue fijando el punto, con su dirección por geocodificación inversa.
- Q: ¿Qué mapa base? → A: Teselas raster de OpenStreetMap con su atribución obligatoria, en ambos temas; el tema oscuro se pinta en el cliente (inversión de brillo y rotación de tono de la capa raster). Sin ninguna API key. *(Se consideró CARTO `dark_all`, pero al verificar con navegador sus teselas devuelven la marca "API KEY REQUIRED".)*
- Q: ¿Se conserva el aspecto del heatmap (ruido de "nubes" y re-escalado de colores)? → A: No. Al revisar el código se encontró que el raster multiplica la probabilidad hasta × 4.2 cuando los valores son bajos y le suma textura de ruido (H-35): una probabilidad de 8 % se pintaba con el color de 34 %. Se reemplaza por una escala fija 0–100 % con leyenda, interpolada entre los puntos predichos (sin ruido). Es un cambio de presentación a favor de no mostrar datos inventados (constitución VII).
- Q: ¿Cómo se rotula la ruta alternativa? → A: Según su tipo: "Ruta más seca" (`dryest`) o "Ruta más corta" (`shortest`), con su tiempo; hoy siempre dice "más seca".
- Q: ¿Navegación 3D? → A: MapLibre soporta inclinación (`pitch`) y rumbo (`bearing`): se conservan la cámara inclinada, el seguimiento de posición y la orientación del dispositivo con el mismo suavizado.

## User Scenarios & Testing *(mandatory)*

Usuarios: **la persona que usa la app** en el celular o el navegador.

### User Story 1 - Ver el mapa de la ciudad con el heatmap de lluvia (Priority: P1)

**Why this priority**: hoy el mapa no carga sin una key de Google con facturación (H-19).

**Independent Test**: abrir `/` sin ninguna key y ver el mapa con el heatmap y su leyenda.

**Acceptance Scenarios**:

1. **Given** el stack sin API keys, **When** se abre el mapa de la ciudad, **Then** se ven las teselas, la atribución de OSM y el heatmap de 81 puntos.
2. **Given** probabilidades predichas, **When** se pinta el heatmap, **Then** el color de cada punto corresponde a su probabilidad en una escala fija mostrada en la leyenda.

---

### User Story 2 - Planificar un viaje buscando direcciones (Priority: P1)

**Independent Test**: buscar "Parque Explora" como origen y "Estadio Atanasio Girardot" como destino, planificar y ver el resultado.

**Acceptance Scenarios**:

1. **Given** un texto, **When** se presiona buscar, **Then** se listan hasta 5 lugares; al elegir uno, se fija el punto en el mapa.
2. **Given** un toque en el mapa, **When** se fija el punto, **Then** se muestra su dirección.
3. **Given** origen, destino y paradas, **When** se planifica, **Then** se navega al resultado con la ruta dibujada, los marcadores y la alerta.

---

### User Story 3 - Resultado y alternativa (Priority: P2)

**Acceptance Scenarios**:

1. **Given** un viaje con alternativa, **When** se ve el resultado, **Then** el botón dice "Ver ruta más seca" o "Ver ruta más corta" según su tipo y alterna la polyline.

---

### User Story 4 - Navegación en ruta con cámara inclinada (Priority: P2)

**Acceptance Scenarios**:

1. **Given** la navegación activa, **When** cambian la posición y el rumbo, **Then** la cámara sigue la posición con inclinación de 45° y rumbo suavizado; al desactivarla vuelve a vista plana.

### Edge Cases

- Búsqueda sin resultados: mensaje "Sin resultados en el Valle de Aburrá".
- Backend de geocodificación caído (503): mensaje de error, el mapa sigue funcionando por toque.
- Sin permiso de ubicación: la navegación muestra el aviso actual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Frontend MUST NOT cargar scripts ni librerías de Google Maps ni requerir `VITE_GOOGLE_MAPS_KEY`.
- **FR-002**: Todos los mapas MUST usar MapLibre GL con teselas OSM y su atribución visible, en tema claro y oscuro.
- **FR-003**: La búsqueda de direcciones MUST usar `GET /api/geocoding/search` al enviar el texto (no por tecla) y `GET /api/geocoding/reverse` al tocar el mapa.
- **FR-004**: La polyline MUST decodificarse en el Frontend (formato *encoded polyline*, precisión 5) y dibujarse con marcadores de origen, paradas y destino, ajustando el encuadre.
- **FR-005**: El heatmap MUST pintar la probabilidad con una escala fija y leyenda, sin re-escalar ni agregar ruido.
- **FR-006**: La navegación MUST conservar inclinación, rumbo suavizado, recentrado y orientación del dispositivo.
- **FR-007**: La alternativa MUST rotularse según su tipo.
- **FR-008**: Las rutas del Frontend (RF-21), el tema claro/oscuro y la UI mobile-first MUST mantenerse.
- **FR-009**: `npm run lint` y `npm run build` MUST pasar, con tests unitarios de la decodificación de polyline y de la escala de color.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 referencias a Google Maps en `apps/frontend` (salvo las fuentes tipográficas de Google Fonts, que no requieren key).
- **SC-002**: El flujo login → mapa → planificar (búsqueda por texto) → resultado → en ruta funciona en el stack sin keys (verificado con navegador automatizado y capturas).
- **SC-003**: El bundle de producción compila y el mapa carga en < 3 s en la red local.

## Assumptions

- El uso de teselas OSM de un portafolio es "uso ligero" según sus políticas; para producción con tráfico se apuntaría a un servidor de teselas propio (configurable por variable de entorno).
