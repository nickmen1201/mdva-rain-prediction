import { useEffect } from 'react';
import { useMap } from '../map/MapView';
import { removeLayer } from '../map/primitives';
import { RAIN_STOPS, gridBounds, rainPixels } from '../map/rainScale';

const ID = 'mdva-rain';
const SIZE = 128;

// Heatmap de probabilidad de lluvia como fuente de imagen de MapLibre (spec 011, FR-005).
// El color sigue una escala fija (la de la leyenda), sin re-escalar ni agregar ruido.
export default function WeatherHeatmapLayer({ points = [], visible = true, opacity = 0.7 }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return undefined;
    if (!visible || points.length < 4) {
      removeLayer(map, ID);
      return undefined;
    }
    const canvas = document.createElement('canvas');
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext('2d');
    ctx.putImageData(new ImageData(rainPixels(points, SIZE), SIZE, SIZE), 0, 0);
    const [w, s, e, n] = gridBounds(points);
    const coordinates = [[w, n], [e, n], [e, s], [w, s]];
    const url = canvas.toDataURL('image/png');

    const source = map.getSource(ID);
    if (source) {
      source.updateImage({ url, coordinates });
    } else {
      map.addSource(ID, { type: 'image', url, coordinates });
      map.addLayer({ id: ID, type: 'raster', source: ID, paint: { 'raster-opacity': opacity, 'raster-resampling': 'linear' } });
    }
    map.setPaintProperty(ID, 'raster-opacity', opacity);
    return undefined;
  }, [map, opacity, points, visible]);

  useEffect(() => () => removeLayer(map, ID), [map]);

  return null;
}

export function RainLegend() {
  const gradient = RAIN_STOPS.map((s) => `rgb(${s.color.join(',')}) ${s.p * 100}%`).join(', ');
  return (
    <div className="rain-legend" aria-label="Escala de probabilidad de lluvia">
      <span className="rain-legend-title">Probabilidad de lluvia (modelo)</span>
      <div className="rain-legend-bar" style={{ background: `linear-gradient(to right, ${gradient})` }} />
      <div className="rain-legend-labels">
        {RAIN_STOPS.map((s) => <span key={s.p}>{s.label}</span>)}
      </div>
    </div>
  );
}
