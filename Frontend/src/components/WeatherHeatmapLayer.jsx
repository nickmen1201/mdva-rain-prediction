import { useEffect, useRef } from 'react';
import { useMap } from '@vis.gl/react-google-maps';
import { BitmapLayer } from '@deck.gl/layers';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';

const COLOR_RANGE = [
  { stop: 0.00, color: [124, 244, 246] },
  { stop: 0.24, color: [72, 211, 238] },
  { stop: 0.46, color: [63, 148, 238] },
  { stop: 0.64, color: [116, 97, 230] },
  { stop: 0.78, color: [246, 211, 77] },
  { stop: 0.90, color: [238, 132, 61] },
  { stop: 1.00, color: [218, 60, 91] },
];

const RASTER_SIZE = 512;

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function smoothstep(edge0, edge1, value) {
  const x = clamp((value - edge0) / (edge1 - edge0));
  return x * x * (3 - 2 * x);
}

function hash2d(x, y) {
  const value = Math.sin(x * 127.1 + y * 311.7) * 43758.5453123;
  return value - Math.floor(value);
}

function valueNoise(x, y) {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const xf = x - x0;
  const yf = y - y0;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const a = hash2d(x0, y0);
  const b = hash2d(x0 + 1, y0);
  const c = hash2d(x0, y0 + 1);
  const d = hash2d(x0 + 1, y0 + 1);
  const xMix1 = a + (b - a) * u;
  const xMix2 = c + (d - c) * u;
  return xMix1 + (xMix2 - xMix1) * v;
}

function cloudNoise(u, v) {
  const low = valueNoise(u * 7.5 + 11.3, v * 7.5 - 4.8);
  const mid = valueNoise(u * 18.0 - 8.1, v * 18.0 + 2.6);
  const high = valueNoise(u * 42.0 + 3.7, v * 42.0 + 19.2);
  return clamp(low * 0.56 + mid * 0.31 + high * 0.13);
}

function interpolateColor(weight) {
  const value = clamp(weight);
  const nextIndex = COLOR_RANGE.findIndex((entry) => value <= entry.stop);
  const upper = COLOR_RANGE[Math.max(1, nextIndex === -1 ? COLOR_RANGE.length - 1 : nextIndex)];
  const lower = COLOR_RANGE[COLOR_RANGE.indexOf(upper) - 1] ?? COLOR_RANGE[0];
  const span = Math.max(upper.stop - lower.stop, 0.0001);
  const t = (value - lower.stop) / span;

  return lower.color.map((channel, index) => Math.round(channel + (upper.color[index] - channel) * t));
}

function getOverlayBounds(points) {
  const lats = points.map((point) => point.lat);
  const lngs = points.map((point) => point.lng);
  const south = Math.min(...lats);
  const north = Math.max(...lats);
  const west = Math.min(...lngs);
  const east = Math.max(...lngs);
  const latPad = (north - south) * 0.12;
  const lngPad = (east - west) * 0.12;

  return {
    south: south - latPad,
    north: north + latPad,
    west: west - lngPad,
    east: east + lngPad,
  };
}

function createWeightSampler(points) {
  const latValues = [...new Set(points.map((point) => Number(point.lat.toFixed(6))))].sort((a, b) => a - b);
  const lngValues = [...new Set(points.map((point) => Number(point.lng.toFixed(6))))].sort((a, b) => a - b);
  const grid = new Map(points.map((point) => [
    `${Number(point.lat.toFixed(6))}:${Number(point.lng.toFixed(6))}`,
    point.weight,
  ]));

  const findInterval = (values, value) => {
    if (value <= values[0]) return [0, 0, 0];
    const last = values.length - 1;
    if (value >= values[last]) return [last, last, 0];

    let low = 0;
    let high = last;
    while (high - low > 1) {
      const mid = Math.floor((low + high) / 2);
      if (values[mid] <= value) low = mid;
      else high = mid;
    }
    const t = (value - values[low]) / (values[high] - values[low]);
    return [low, high, t];
  };

  return (lat, lng) => {
    const [latA, latB, latT] = findInterval(latValues, lat);
    const [lngA, lngB, lngT] = findInterval(lngValues, lng);
    const get = (latIndex, lngIndex) => grid.get(`${latValues[latIndex]}:${lngValues[lngIndex]}`) ?? 0;

    const southWest = get(latA, lngA);
    const southEast = get(latA, lngB);
    const northWest = get(latB, lngA);
    const northEast = get(latB, lngB);
    const southMix = southWest + (southEast - southWest) * lngT;
    const northMix = northWest + (northEast - northWest) * lngT;
    return southMix + (northMix - southMix) * latT;
  };
}

function buildRainRaster(points) {
  if (!points.length) return null;

  const bounds = getOverlayBounds(points);
  const sample = createWeightSampler(points);
  const canvas = document.createElement('canvas');
  canvas.width = RASTER_SIZE;
  canvas.height = RASTER_SIZE;
  const context = canvas.getContext('2d');
  const image = context.createImageData(RASTER_SIZE, RASTER_SIZE);
  const innerEdge = 0.18;

  for (let y = 0; y < RASTER_SIZE; y += 1) {
    for (let x = 0; x < RASTER_SIZE; x += 1) {
      const u = x / (RASTER_SIZE - 1);
      const v = y / (RASTER_SIZE - 1);
      const lng = bounds.west + (bounds.east - bounds.west) * u;
      const lat = bounds.north - (bounds.north - bounds.south) * v;
      const rawWeight = clamp(sample(lat, lng));
      const texture = cloudNoise(u, v);
      const rainShape = smoothstep(0.12, 0.72, rawWeight);
      const brokenCoverage = texture * 0.22 + cloudNoise(u + 0.19, v - 0.07) * 0.12;
      const texturedWeight = clamp(rawWeight + (texture - 0.5) * 0.24 * rainShape);
      const localThreshold = 0.16 + brokenCoverage;
      const visibility = smoothstep(localThreshold, localThreshold + 0.18, texturedWeight);
      const [r, g, b] = interpolateColor(texturedWeight);
      const edgeDistance = Math.min(u, 1 - u, v, 1 - v);
      const edgeFade = smoothstep(0, innerEdge, edgeDistance);
      const alpha = Math.round((24 + texturedWeight * 178) * visibility * edgeFade);
      const index = (y * RASTER_SIZE + x) * 4;

      image.data[index] = r;
      image.data[index + 1] = g;
      image.data[index + 2] = b;
      image.data[index + 3] = alpha;
    }
  }

  context.putImageData(image, 0, 0);

  const blurredCanvas = document.createElement('canvas');
  blurredCanvas.width = RASTER_SIZE;
  blurredCanvas.height = RASTER_SIZE;
  const blurContext = blurredCanvas.getContext('2d');
  blurContext.filter = 'blur(1.4px)';
  blurContext.drawImage(canvas, 0, 0);
  return {
    canvas: blurredCanvas,
    bounds: [bounds.west, bounds.south, bounds.east, bounds.north],
  };
}

export default function WeatherHeatmapLayer({ points = [], visible = true }) {
  const map = useMap();
  const overlayRef = useRef(null);

  useEffect(() => {
    if (!map || !visible || !points.length) {
      overlayRef.current?.setProps({ layers: [] });
      return;
    }

    if (!overlayRef.current) {
      overlayRef.current = new GoogleMapsOverlay({ layers: [] });
      overlayRef.current.setMap(map);
    }

    const raster = buildRainRaster(points);
    if (!raster) {
      overlayRef.current.setProps({ layers: [] });
      return;
    }

    const layer = new BitmapLayer({
      id: 'mdva-rain-cloud',
      bounds: raster.bounds,
      image: raster.canvas,
      opacity: 0.92,
      pickable: false,
    });

    overlayRef.current.setProps({ layers: [layer] });
  }, [map, points, visible]);

  useEffect(() => () => {
    overlayRef.current?.setMap(null);
    overlayRef.current = null;
  }, []);

  return null;
}
