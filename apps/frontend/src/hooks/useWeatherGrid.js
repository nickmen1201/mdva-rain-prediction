import { useEffect, useMemo, useRef, useState } from 'react';
import { predictWeatherGrid } from '../api/client';

const MEDELLIN_CENTER = { lat: 6.2442, lng: -75.5812 };
const CACHE_TTL_MS = 180_000;
const weatherGridCache = new Map();

function toRad(value) {
  return value * Math.PI / 180;
}

function distanceMeters(a, b) {
  if (!a || !b) return Infinity;
  const earthRadius = 6371000;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const x = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat))
    * Math.sin(dLng / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function roundCoord(value) {
  return Math.round(value * 1000) / 1000;
}

function cacheKey(center, gridSize, spacingKm) {
  return `${roundCoord(center.lat)}:${roundCoord(center.lng)}:${gridSize}:${spacingKm}`;
}

function generateGrid(center, gridSize, spacingKm) {
  const half = Math.floor(gridSize / 2);
  const latStep = spacingKm / 111.32;
  const lngStep = spacingKm / (111.32 * Math.cos(toRad(center.lat)));
  const points = [];

  for (let row = -half; row <= half; row += 1) {
    for (let col = -half; col <= half; col += 1) {
      points.push({
        lat: Number((center.lat + row * latStep).toFixed(6)),
        lng: Number((center.lng + col * lngStep).toFixed(6)),
      });
    }
  }

  return points;
}

// Probabilidades del modelo tal cual (spec 011): un punto sin probabilidad se descarta, nunca se pinta
// como 0 %. La interpolación entre puntos la hace la capa del mapa (bilineal, sin extrapolar).
function normalizeResults(resultados = []) {
  return resultados
    .filter((point) => Number.isFinite(Number(point.probabilidadRf)) && point.probabilidadRf !== null)
    .map((point) => ({
      lat: point.lat,
      lng: point.lng,
      weight: Math.max(0, Math.min(1, Number(point.probabilidadRf))),
    }));
}

export default function useWeatherGrid({
  enabled,
  center = MEDELLIN_CENTER,
  gridSize = 7,
  spacingKm = 0.85,
  refreshMs = CACHE_TTL_MS,
  minMoveMeters = 0,
} = {}) {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const lastFetchCenterRef = useRef(null);

  const effectiveCenter = useMemo(() => center ?? MEDELLIN_CENTER, [center]);

  useEffect(() => {
    if (!enabled || !effectiveCenter) {
      setLoading(false);
      setError(null);
      return;
    }

    const lastCenter = lastFetchCenterRef.current;
    const shouldUseNewCenter = !lastCenter
      || minMoveMeters <= 0
      || distanceMeters(lastCenter, effectiveCenter) >= minMoveMeters;
    const fetchCenter = shouldUseNewCenter ? effectiveCenter : lastCenter;
    const key = cacheKey(fetchCenter, gridSize, spacingKm);

    if (shouldUseNewCenter) {
      lastFetchCenterRef.current = fetchCenter;
    }

    let intervalId;
    const controller = new AbortController();

    const fetchGrid = async ({ force = false } = {}) => {
      const cached = weatherGridCache.get(key);
      if (!force && cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
        setPoints(cached.points);
        setError(null);
        return;
      }

      setLoading(true);
      try {
        const response = await predictWeatherGrid(
          generateGrid(fetchCenter, gridSize, spacingKm),
          { signal: controller.signal },
        );
        const nextPoints = normalizeResults(response?.resultados);
        weatherGridCache.set(key, { points: nextPoints, timestamp: Date.now() });
        setPoints(nextPoints);
        setError(null);
      } catch (err) {
        if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
          setError('No se pudo cargar la capa de lluvia.');
          setPoints([]);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchGrid();
    intervalId = window.setInterval(() => fetchGrid({ force: true }), refreshMs);

    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [enabled, effectiveCenter, gridSize, spacingKm, refreshMs, minMoveMeters]);

  return { points, loading, error };
}
