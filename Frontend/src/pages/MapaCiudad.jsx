import { Map } from '@vis.gl/react-google-maps';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import WeatherHeatmapLayer from '../components/WeatherHeatmapLayer';
import WeatherHeatmapToggle from '../components/WeatherHeatmapToggle';
import useWeatherGrid from '../hooks/useWeatherGrid';

const MEDELLIN_CENTER = { lat: 6.2442, lng: -75.5812 };
const RAIN_HEATMAP_STORAGE_KEY = 'mdva-rain-heatmap-enabled';

function formatKm(meters) {
  if (meters == null) return '—';
  return `${(meters / 1000).toFixed(1)} km`;
}

function wasTripInterrupted(summary) {
  return (summary?.pendingStopsCount ?? 0) > 0 || !summary?.horaFin;
}

function formatDuration(summary) {
  if (summary?.horaInicio && summary?.horaFin) {
    const start = new Date(summary.horaInicio).getTime();
    const end = new Date(summary.horaFin).getTime();
    if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
      return `${Math.max(1, Math.round((end - start) / 60000))} min`;
    }
  }
  return summary?.tiempoEstimadoMin != null ? `${summary.tiempoEstimadoMin} min` : '—';
}

function climateLabel(summary) {
  const pred = summary?.prediccionLluvia;
  const prob = pred?.probabilidadRf;
  if (summary?.alertaNivel === 'ROJO') return 'LLUVIA FUERTE';
  if (summary?.alertaNivel === 'AMARILLO' || (prob != null && prob >= 0.55)) return 'LLUVIA POSIBLE';
  if (prob != null && prob < 0.25) return 'CLIMA FAVORABLE';
  return summary?.alertaNivel ?? 'ESTABLE';
}

export default function MapaCiudad() {
  const navigate = useNavigate();
  const location = useLocation();
  const [tripSummary, setTripSummary] = useState(() => location.state?.tripSummary ?? null);
  const [heatmapEnabled, setHeatmapEnabled] = useState(
    () => localStorage.getItem(RAIN_HEATMAP_STORAGE_KEY) !== 'false',
  );
  const { points, loading, error } = useWeatherGrid({
    enabled: heatmapEnabled,
    center: MEDELLIN_CENTER,
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

  const closeSummary = () => {
    setTripSummary(null);
    navigate('.', { replace: true, state: null });
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Map
        defaultCenter={MEDELLIN_CENTER}
        defaultZoom={13}
        mapId="mdva-map"
        colorScheme="DARK"
        gestureHandling="greedy"
        disableDefaultUI={false}
        style={{ width: '100%', height: '100%' }}
      >
        <WeatherHeatmapLayer points={points} visible={heatmapEnabled && !error} />
      </Map>

      <div className="map-controls top-right">
        <WeatherHeatmapToggle
          enabled={heatmapEnabled}
          loading={loading}
          onToggle={toggleHeatmap}
        />
      </div>

      {heatmapEnabled && error && (
        <div className="map-toast map-toast-warning">
          {error}
        </div>
      )}

      {tripSummary && (
        <div className="arrival-modal-overlay">
          <div className="arrival-modal-card trip-summary-modal">
            <div className="section-heading">Viaje finalizado</div>
            <h2>Resumen del trayecto</h2>
            <p>
              De {tripSummary.origen?.displayName ?? tripSummary.nombreOrigen ?? 'Origen'} a {tripSummary.destino?.displayName ?? tripSummary.nombreDestino ?? 'Destino'}.
            </p>
            <div className="trip-summary-grid">
              <div>
                <span>Tiempo</span>
                <strong>{formatDuration(tripSummary)}</strong>
              </div>
              <div>
                <span>Distancia</span>
                <strong>{wasTripInterrupted(tripSummary) ? 'VIAJE NO FINALIZADO' : formatKm(tripSummary.distanciaMetros)}</strong>
              </div>
              <div>
                <span>Clima</span>
                <strong>{climateLabel(tripSummary)}</strong>
              </div>
              <div>
                <span>Estado</span>
                <strong>
                  {(tripSummary.pendingStopsCount ?? 0) > 0
                    ? `${tripSummary.pendingStopsCount} DESTINO${tripSummary.pendingStopsCount === 1 ? '' : 'S'} SIN VISITAR`
                    : 'TRAYECTO CERRADO'}
                </strong>
              </div>
            </div>
            {tripSummary.completedStops?.length > 0 && (
              <div className="queue-preview trip-summary-stops">
                {tripSummary.completedStops.map((stop, index) => (
                  <div key={`${stop.lat ?? index}-${stop.lng ?? index}-${index}`}>
                    <span>{index === 0 ? 'Origen' : index === tripSummary.completedStops.length - 1 ? 'Destino' : `Parada ${index}`}</span>
                    <strong>{stop.displayName ?? 'Punto del viaje'}</strong>
                  </div>
                ))}
              </div>
            )}
            <div className="arrival-actions">
              <button className="btn btn-primary" onClick={() => navigate('/planificar')}>
                Nuevo viaje
              </button>
              <button className="btn btn-secondary" onClick={() => navigate('/historial/1')}>
                Ver historial
              </button>
              <button className="btn btn-secondary" onClick={closeSummary}>
                Volver al mapa
              </button>
            </div>
          </div>
        </div>
      )}
      
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
