// Utilidades geográficas puras (spec 011): sin dependencias del mapa, probadas con vitest.

/**
 * Decodifica una "encoded polyline" (precisión 1e-5), el formato que devuelve el routing service.
 * @returns {{lat: number, lng: number}[]}
 */
export function decodePolyline(encoded) {
  if (!encoded) return [];
  const points = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  const next = () => {
    let result = 0;
    let shift = 0;
    let byte;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    return result & 1 ? ~(result >> 1) : result >> 1;
  };

  while (index < encoded.length) {
    lat += next();
    lng += next();
    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }
  return points;
}

/** [lng, lat] para MapLibre a partir de {lat, lng}. */
export const toLngLat = (p) => [p.lng, p.lat];

/** Caja [[oeste, sur], [este, norte]] que contiene los puntos, o null si no hay puntos. */
export function boundsOf(points) {
  const valid = points.filter((p) => Number.isFinite(p?.lat) && Number.isFinite(p?.lng));
  if (!valid.length) return null;
  const lats = valid.map((p) => p.lat);
  const lngs = valid.map((p) => p.lng);
  return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
}
