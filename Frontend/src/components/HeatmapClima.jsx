import { useEffect, useRef, useState } from 'react';
import { useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { predictWeatherGrid } from '../api/client';

/**
 * HU036 — Capa de calor de probabilidad de lluvia sobre el mapa.
 *
 * Genera una grilla de N×N puntos centrada en `centro` con `spacing` grados
 * entre cada punto, llama al backend /api/weather/predict-grid y renderiza
 * los resultados como HeatmapLayer de Google Maps (librería visualization).
 *
 * Refresca cada `refreshMs` (default 3 min) para no agotar el quota Google.
 *
 * Spacing 0.005° ≈ 550m en el ecuador → grilla 5×5 cubre ~2.7 km de lado.
 */
export default function HeatmapClima({
  centro = { lat: 6.2442, lng: -75.5812 },
  size = 5,
  spacing = 0.005,
  refreshMs = 180_000,
  visible = true,
}) {
  const map = useMap();
  const visualizationLib = useMapsLibrary('visualization');
  const heatmapRef = useRef(null);
  const [puntos, setPuntos] = useState([]);
  const [cargando, setCargando] = useState(false);

  // Generar grilla y cargar predicciones
  useEffect(() => {
    if (!visible) return;

    let cancelled = false;
    const cargar = async () => {
      setCargando(true);
      const grid = [];
      const half = Math.floor(size / 2);
      for (let i = -half; i <= half; i++) {
        for (let j = -half; j <= half; j++) {
          grid.push({
            lat: centro.lat + i * spacing,
            lng: centro.lng + j * spacing,
          });
        }
      }

      try {
        const res = await predictWeatherGrid(grid);
        if (!cancelled && res?.resultados) setPuntos(res.resultados);
      } catch (err) {
        console.error('HeatmapClima: error al cargar grid', err);
      } finally {
        if (!cancelled) setCargando(false);
      }
    };

    cargar();
    const timer = setInterval(cargar, refreshMs);
    return () => { cancelled = true; clearInterval(timer); };
  }, [centro.lat, centro.lng, size, spacing, refreshMs, visible]);

  // Renderizar HeatmapLayer
  useEffect(() => {
    if (!map || !visualizationLib || !puntos.length) return;

    const data = puntos.map((p) => ({
      location: new window.google.maps.LatLng(p.lat, p.lng),
      weight: p.probabilidadRf ?? 0,
    }));

    if (heatmapRef.current) {
      heatmapRef.current.setData(data);
      heatmapRef.current.setMap(visible ? map : null);
    } else {
      // dissipating: false → radius se interpreta en METROS (no píxeles), por
      // lo que el heatmap mantiene el mismo tamaño geográfico al hacer zoom in/out.
      // Sin esto, a zoom alto cubre todo y a zoom bajo se ve como 25 puntos sueltos.
      // radius en metros ≈ spacing × 111000 / sqrt(2) para overlap natural entre celdas.
      const radiusMetros = Math.round(spacing * 111000 * 0.85);
      heatmapRef.current = new visualizationLib.HeatmapLayer({
        data,
        map: visible ? map : null,
        dissipating: false,
        radius: radiusMetros,
        opacity: 0.6,
        maxIntensity: 1.0,
        gradient: [
          'rgba(0, 0, 0, 0)',
          'rgba(74, 240, 160, 0.5)',  // verde — prob baja
          'rgba(240, 200, 74, 0.7)',  // amarillo — prob media
          'rgba(240, 120, 74, 0.8)',  // naranja — prob alta
          'rgba(240, 74, 74, 0.9)',   // rojo — prob crítica
        ],
      });
    }

    return () => {
      // No removemos en cleanup para permitir update incremental;
      // solo desmontamos cuando el componente se va.
    };
  }, [map, visualizationLib, puntos, visible]);

  // Cleanup final
  useEffect(() => () => {
    heatmapRef.current?.setMap(null);
    heatmapRef.current = null;
  }, []);

  if (!visible) return null;

  return (
    <div style={{
      position: 'absolute',
      bottom: '10px',
      right: '10px',
      background: 'rgba(17, 19, 24, 0.85)',
      backdropFilter: 'blur(8px)',
      padding: '6px 10px',
      borderRadius: '6px',
      fontSize: '0.7rem',
      color: 'var(--muted)',
      border: '1px solid var(--border)',
      zIndex: 5,
    }}>
      {cargando ? '⟳ Cargando clima...' : `☔ Probabilidad de lluvia (${puntos.length} pts)`}
    </div>
  );
}
