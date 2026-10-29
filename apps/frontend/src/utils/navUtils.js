/**
 * Devuelve el ícono de maniobra apropiado basado en el texto de la instrucción.
 * Usa texto simple para máxima compatibilidad sin iconos externos.
 */
export function getManeuvreIcon(instruccion = '') {
  const t = instruccion.toLowerCase();
  if (t.includes('izquierda') || t.includes('left'))   return '↰';
  if (t.includes('derecha')   || t.includes('right'))  return '↱';
  if (t.includes('rotar')     || t.includes('roundabout')) return '↻';
  if (t.includes('u-turn')    || t.includes('media vuelta')) return '↩';
  if (t.includes('destino')   || t.includes('llegada') || t.includes('arrive')) return '🏁';
  return '↑';
}

/**
 * Distancia Haversine entre dos puntos en metros.
 */
export function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180)
    * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Formatea metros en "X km" o "X m".
 */
export function formatDistancia(metros) {
  if (metros == null) return '—';
  if (metros >= 1000) return `${(metros / 1000).toFixed(1)} km`;
  return `${Math.round(metros)} m`;
}

/**
 * Dado un array de pasos y la posición actual, retorna el índice del paso activo.
 */
export function calcularPasoActivo(pasos = [], posicion) {
  if (!posicion || !pasos.length) return 0;
  let minDist = Infinity;
  let idx = 0;
  pasos.forEach((paso, i) => {
    if (paso.startLat == null) return;
    const d = haversine(posicion.lat, posicion.lng, paso.startLat, paso.startLng);
    if (d < minDist) { minDist = d; idx = i; }
  });
  return idx;
}

/**
 * Calcula distancia total restante desde la posición actual hasta el final.
 */
export function calcularDistanciaRestante(pasos = [], pasoActual, posicion) {
  if (!posicion || !pasos.length) return null;
  let total = 0;
  pasos.slice(pasoActual).forEach(p => { total += p.distanciaMetros ?? 0; });
  // Resta la distancia ya recorrida dentro del paso actual
  if (pasos[pasoActual]?.startLat != null) {
    const dentroDelPaso = haversine(posicion.lat, posicion.lng, pasos[pasoActual].startLat, pasos[pasoActual].startLng);
    total = Math.max(0, total - dentroDelPaso);
  }
  return total;
}
