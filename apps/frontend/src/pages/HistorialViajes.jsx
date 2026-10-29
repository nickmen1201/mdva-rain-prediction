import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getHistorial } from '../api/client';
import TarjetaViaje from '../components/TarjetaViaje';

export default function HistorialViajes() {
  const { idUsuario }           = useParams();
  const [viajes,  setViajes]    = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error,   setError]     = useState(null);

  useEffect(() => {
    getHistorial(idUsuario)
      .then(setViajes)
      .catch(() => setError('No se pudo cargar el historial.'))
      .finally(() => setLoading(false));
  }, [idUsuario]);

  return (
    <div className="page-content">
      <h1 className="page-title fade-up">Historial</h1>
      <p className="page-subtitle fade-up">Usuario #{idUsuario}</p>

      {loading && (
        <div style={{ color: 'var(--muted)', fontFamily: 'DM Mono', fontSize: '0.85rem' }}>
          <span className="spinner" style={{ marginRight: '0.5rem' }} />
          Cargando viajes...
        </div>
      )}

      {error && <div className="error-box">{error}</div>}

      {!loading && !error && viajes.length === 0 && (
        <div style={{ color: 'var(--muted)', fontFamily: 'DM Mono', fontSize: '0.9rem', marginTop: '2rem' }}>
          No hay viajes registrados para este usuario.
        </div>
      )}

      {!loading && viajes.length > 0 && (
        <div className="viaje-list fade-up-2">
          {viajes.map((v) => (
            <TarjetaViaje key={v.idViaje} viaje={v} />
          ))}
        </div>
      )}
    </div>
  );
}
