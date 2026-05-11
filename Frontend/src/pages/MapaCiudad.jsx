import { useState } from 'react';
import { Map } from '@vis.gl/react-google-maps';
import { useNavigate } from 'react-router-dom';
import HeatmapClima from '../components/HeatmapClima';
import ForecastHorario from '../components/ForecastHorario';

const MEDELLIN_CENTRO = { lat: 6.2442, lng: -75.5812 };

export default function MapaCiudad() {
  const navigate = useNavigate();
  const [heatmapVisible, setHeatmapVisible] = useState(true);

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
        <HeatmapClima
          centro={MEDELLIN_CENTRO}
          size={5}
          spacing={0.02}
          visible={heatmapVisible}
        />
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

      {/* Toggle heatmap — esquina superior derecha */}
      <button
        onClick={() => setHeatmapVisible((v) => !v)}
        className="btn-icon nav-hud"
        aria-pressed={heatmapVisible}
        title={heatmapVisible ? 'Ocultar capa de lluvia' : 'Mostrar capa de lluvia'}
        style={{
          position: 'absolute',
          top: '1rem',
          right: '1rem',
          zIndex: 10,
          fontSize: '1.1rem',
        }}
      >
        {heatmapVisible ? '☔' : '🌤'}
      </button>

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
        <div style={{
          background: 'rgba(17, 19, 24, 0.85)',
          backdropFilter: 'blur(10px)',
          padding: '15px 25px',
          borderRadius: '10px',
          border: '1px solid var(--border)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          textAlign: 'center'
        }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '8px', color: 'var(--text)' }}>Explora la Ciudad</h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--muted)', marginBottom: '16px' }}>
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
