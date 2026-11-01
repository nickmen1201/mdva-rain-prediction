// Escala de color fija de probabilidad de lluvia y raster del heatmap (spec 011, FR-005).
//
// La versión anterior multiplicaba la probabilidad hasta ×4.2 cuando los valores eran bajos y le
// sumaba ruido de "nubes" (H-35): un 8 % se veía como 34 %. Aquí el color depende solo de la
// probabilidad interpolada entre los puntos predichos, con la misma escala que muestra la leyenda.

export const RAIN_STOPS = [
  { p: 0.0, color: [124, 244, 246], label: '0 %' },
  { p: 0.2, color: [72, 211, 238], label: '20 %' },
  { p: 0.4, color: [246, 211, 77], label: '40 %' }, // umbral AMARILLO
  { p: 0.7, color: [238, 132, 61], label: '70 %' }, // umbral ROJO
  { p: 1.0, color: [218, 60, 91], label: '100 %' },
];

const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));

/** Color RGB para una probabilidad en [0, 1] (interpolación lineal entre los cortes de la escala). */
export function rainColor(p) {
  const v = clamp(p);
  for (let i = 1; i < RAIN_STOPS.length; i += 1) {
    const a = RAIN_STOPS[i - 1];
    const b = RAIN_STOPS[i];
    if (v <= b.p) {
      const t = (v - a.p) / (b.p - a.p);
      return a.color.map((c, k) => Math.round(c + (b.color[k] - c) * t));
    }
  }
  return RAIN_STOPS[RAIN_STOPS.length - 1].color;
}

/** Opacidad: crece con la probabilidad para que las zonas secas no tapen el mapa (sin re-escalar el color). */
export const rainAlpha = (p) => Math.round(40 + clamp(p) * 170);

/**
 * Muestreador bilineal sobre la malla regular de puntos {lat, lng, weight}.
 * Fuera de la malla devuelve null (no se pinta: no se extrapola).
 */
export function gridSampler(points) {
  const lats = [...new Set(points.map((p) => +p.lat.toFixed(6)))].sort((a, b) => a - b);
  const lngs = [...new Set(points.map((p) => +p.lng.toFixed(6)))].sort((a, b) => a - b);
  const values = new Map(points.map((p) => [`${+p.lat.toFixed(6)}:${+p.lng.toFixed(6)}`, p.weight]));

  const locate = (axis, v) => {
    if (v < axis[0] || v > axis[axis.length - 1]) return null;
    let i = 0;
    while (i < axis.length - 2 && axis[i + 1] <= v) i += 1;
    const span = axis[i + 1] - axis[i] || 1;
    return [i, Math.min(i + 1, axis.length - 1), (v - axis[i]) / span];
  };

  return (lat, lng) => {
    const a = locate(lats, lat);
    const b = locate(lngs, lng);
    if (!a || !b) return null;
    const get = (i, j) => values.get(`${lats[i]}:${lngs[j]}`);
    const corners = [get(a[0], b[0]), get(a[0], b[1]), get(a[1], b[0]), get(a[1], b[1])];
    if (corners.some((c) => c == null)) return null;
    const [sw, se, nw, ne] = corners;
    const south = sw + (se - sw) * b[2];
    const north = nw + (ne - nw) * b[2];
    return south + (north - south) * a[2];
  };
}

/** Caja de la malla: [oeste, sur, este, norte]. */
export function gridBounds(points) {
  // Mismo redondeo que el muestreador, para que los bordes caigan dentro de la malla
  const lats = points.map((p) => +p.lat.toFixed(6));
  const lngs = points.map((p) => +p.lng.toFixed(6));
  return [Math.min(...lngs), Math.min(...lats), Math.max(...lngs), Math.max(...lats)];
}

/** Píxeles RGBA (size × size) del heatmap; la fila 0 es el borde norte. */
export function rainPixels(points, size = 128) {
  const sample = gridSampler(points);
  const [west, south, east, north] = gridBounds(points);
  const data = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const lat = north - ((north - south) * y) / (size - 1);
      const lng = west + ((east - west) * x) / (size - 1);
      const p = sample(lat, lng);
      const k = (y * size + x) * 4;
      if (p == null) continue;
      const [r, g, b] = rainColor(p);
      data[k] = r;
      data[k + 1] = g;
      data[k + 2] = b;
      data[k + 3] = rainAlpha(p);
    }
  }
  return data;
}
