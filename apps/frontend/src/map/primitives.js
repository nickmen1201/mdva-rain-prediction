import maplibregl from 'maplibre-gl';
import { toLngLat } from './geo';

// Primitivas de dibujo sobre MapLibre (spec 011): líneas GeoJSON y marcadores circulares.

/** Dibuja (o actualiza) una línea con id fijo. `points` = [{lat, lng}]. */
export function setLine(map, id, points, { color = '#4af0a0', width = 4, opacity = 0.9, dash } = {}) {
  const data = { type: 'Feature', geometry: { type: 'LineString', coordinates: points.map(toLngLat) } };
  const source = map.getSource(id);
  if (source) {
    source.setData(data);
  } else {
    map.addSource(id, { type: 'geojson', data });
    map.addLayer({
      id,
      type: 'line',
      source: id,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': color, 'line-width': width, 'line-opacity': opacity, ...(dash ? { 'line-dasharray': dash } : {}) },
    });
  }
  map.setPaintProperty(id, 'line-color', color);
  map.setPaintProperty(id, 'line-width', width);
  map.setPaintProperty(id, 'line-opacity', opacity);
}

export function removeLayer(map, id) {
  if (!map?.getStyle()) return;
  if (map.getLayer(id)) map.removeLayer(id);
  if (map.getSource(id)) map.removeSource(id);
}

/** Marcador circular (reemplaza los SymbolPath.CIRCLE del proveedor anterior). */
export function circleMarker(map, point, { color = '#4af0a0', size = 18, title, border = '#0a0c10' } = {}) {
  const el = document.createElement('div');
  el.className = 'map-dot';
  el.title = title ?? '';
  Object.assign(el.style, {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: '50%',
    background: color,
    border: `2px solid ${border}`,
    boxShadow: '0 0 0 2px rgba(255,255,255,0.25)',
  });
  return new maplibregl.Marker({ element: el }).setLngLat(toLngLat(point)).addTo(map);
}
