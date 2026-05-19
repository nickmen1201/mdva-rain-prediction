import { useState } from 'react';
import { Map } from '@vis.gl/react-google-maps';
import { useNavigate } from 'react-router-dom';
import ForecastHorario from '../components/ForecastHorario';
import WeatherHeatmapLayer from '../components/WeatherHeatmapLayer';
import WeatherHeatmapToggle from '../components/WeatherHeatmapToggle';
import useWeatherGrid from '../hooks/useWeatherGrid';

const MEDELLIN_CENTRO = { lat: 6.2442, lng: -75.5812 };
const RAIN_HEATMAP_STORAGE_KEY = 'mdva-rain-heatmap-enabled';

export default function MapaCiudad() {
  const navigate = useNavigate();
  const [heatmapEnabled, setHeatmapEnabled] = useState(
    () => localStorage.getItem(RAIN_HEATMAP_STORAGE_KEY) !== 'false',
  );
  const { points, loading, error } = useWeatherGrid({
    enabled: heatmapEnabled,
    center: MEDELLIN_CENTRO,
    gridSize: 9,
    spacingKm: 0.78,
  });

  const toggleHeatmap = () => {
    setHeatmapEnabled((current) => {
      const next = !current;
      localStorage.setItem(RAIN_HEATMAP_STORAGE_KEY, String(next));
      return next;
    });
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Map
        defaultCenter={MEDELLIN_CENTRO}
        defaultZoom={13}
        mapId="mdva-map"
        colorScheme="DARK"
        gestureHandling="greedy"
        disableDefaultUI={false}
        style={{ width: '100%', height: '100%' }}
      >
        <WeatherHeatmapLayer points={points} visible={heatmapEnabled && !error} />
      </Map>

      {/* Forecast 6h flotante — esquina superior izquierda */}
      <div style={{
        position: 'absolute',
        top: '1rem',
        left: '1rem',
        zIndex: 10,
      }}>
        <ForecastHorario centro={MEDELLIN_CENTRO} horas={6} />
      </div>

      <div className="map-controls top-right">
        <WeatherHeatmapToggle
          enabled={heatmapEnabled}
          loading={loading}
          onToggle={toggleHeatmap}
        />
      </div>

      {heatmapEnabled && error && (
        <div className="map-toast map-toast-warning">{error}</div>
      )}

      {/* CTA inferior */}
      <div style={{
        position: 'absolute',
        bottom: '30px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 10,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '10px'
      }}>
        <div className="city-map-cta-card">
          <h2 className="city-map-cta-title">Explora la Ciudad</h2>
          <p className="city-map-cta-copy">
            Revisa el estado actual o planifica un viaje inteligente.
          </p>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/planificar')}
          >
            Planificar nuevo viaje
          </button>
        </div>
      </div>
    </div>
  );
}
