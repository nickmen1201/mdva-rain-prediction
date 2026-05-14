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

function normalizeResults(resultados = []) {
  return resultados.map((point) => {
    const probability = Number(point.probabilidadRf ?? 0);
    return {
      lat: point.lat,
      lng: point.lng,
      weight: Math.max(0, Math.min(1, probability)),
    };
  });
}

function interpolateSurface(points, samplesPerSide = 31) {
  if (points.length < 4) return points;

  const lats = points.map((point) => point.lat);
  const lngs = points.map((point) => point.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const latStep = (maxLat - minLat) / (samplesPerSide - 1);
  const lngStep = (maxLng - minLng) / (samplesPerSide - 1);
  const surface = [];

  for (let row = 0; row < samplesPerSide; row += 1) {
    for (let col = 0; col < samplesPerSide; col += 1) {
      const lat = minLat + latStep * row;
      const lng = minLng + lngStep * col;
      let numerator = 0;
      let denominator = 0;

      points.forEach((point) => {
        const dist = Math.max(distanceMeters({ lat, lng }, point), 25);
        const influence = 1 / (dist ** 1.8);
        numerator += point.weight * influence;
        denominator += influence;
      });

      surface.push({
        lat: Number(lat.toFixed(6)),
        lng: Number(lng.toFixed(6)),
        weight: denominator > 0 ? numerator / denominator : 0,
      });
    }
  }

  return surface;
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
        const nextPoints = interpolateSurface(normalizeResults(response?.resultados));
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
