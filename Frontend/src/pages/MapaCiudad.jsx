import { Map } from '@vis.gl/react-google-maps';
import { useNavigate } from 'react-router-dom';

export default function MapaCiudad() {
  const navigate = useNavigate();

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Map
        defaultCenter={{ lat: 6.2442, lng: -75.5812 }} // Medellin center
        defaultZoom={13}
        mapId="mdva-map"
        colorScheme="DARK"
        gestureHandling="greedy"
        disableDefaultUI={false}
        style={{ width: '100%', height: '100%' }}
      />
      
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
          <h2 style={{ fontSize: '1.2rem', marginBottom: '5px', color: 'var(--text)' }}>Explora la Ciudad</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '15px' }}>
            Revisa el estado actual o planifica un viaje inteligente.
          </p>
          <button 
            className="btn btn-primary"
            onClick={() => navigate('/planificar')}
          >
            Planificar nuevo viaje →
          </button>
        </div>
      </div>
    </div>
  );
}
