import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { getViajeById, finalizarViaje } from '../api/client';
import MapaRuta from '../components/MapaRuta';
import AlertaClimatica from '../components/AlertaClimatica';

export default function ResultadoViaje() {
  const { id }       = useParams();
  const location     = useLocation();
  const navigate     = useNavigate();
  const [viaje,      setViaje]      = useState(location.state?.viaje ?? null);
  const [loading,    setLoading]    = useState(!viaje);
  const [finalizing, setFinalizing] = useState(false);
  const [error,      setError]      = useState(null);

  useEffect(() => {
    if (viaje) return;
    getViajeById(id)
      .then(setViaje)
      .catch(() => setError('No se pudo cargar el viaje.'))
      .finally(() => setLoading(false));
  }, [id, viaje]);

  const handleFinalizar = async () => {
    setFinalizing(true);
    try {
      await finalizarViaje(id);
    } catch (err) {
      if (err.response?.status !== 409) {
        setError('Error al finalizar el viaje.');
        setFinalizing(false);
        return;
      }
    }
    navigate('/historial/1');
  };

  if (loading) return <div style={{ padding: '3rem', color: 'var(--muted)', fontFamily: 'DM Mono' }}>Cargando viaje...</div>;
  if (error)   return <div className="error-box" style={{ marginTop: '2rem' }}>{error}</div>;
  if (!viaje)  return null;

  const distKm   = viaje.distanciaMetros ? (viaje.distanciaMetros / 1000).toFixed(1) : '—';
  const horaStr  = viaje.horaInicio
    ? new Date(viaje.horaInicio).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <div>
      {/* Header */}
      <div className="fade-up" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
        <div>
          <h1 className="page-title">
            {viaje.origen?.displayName ?? 'Origen'} →<br />
            {viaje.destino?.displayName ?? 'Destino'}
          </h1>
          <p className="page-subtitle">Viaje #{viaje.idViaje} · {horaStr}</p>
        </div>
        {viaje.alertaNivel && (
          <span className={`alerta-badge alerta-${viaje.alertaNivel}`} style={{ marginTop: '0.5rem', fontSize: '0.82rem', padding: '0.4rem 1rem' }}>
            {{ VERDE: '●', AMARILLO: '◆', ROJO: '▲' }[viaje.alertaNivel]} {viaje.alertaNivel}
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="stats-grid fade-up">
        <div className="stat-item">
          <div className="stat-label">Tiempo estimado</div>
          <div className="stat-value">{viaje.tiempoEstimadoMin ?? '—'}</div>
          <div className="stat-unit">minutos</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Tiempo base</div>
          <div className="stat-value" style={{ color: 'var(--muted)' }}>{viaje.tiempoBaseMin ?? '—'}</div>
          <div className="stat-unit">minutos</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Distancia</div>
          <div className="stat-value">{distKm}</div>
          <div className="stat-unit">kilómetros</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Pasos de ruta</div>
          <div className="stat-value">{viaje.pasos?.length ?? '—'}</div>
          <div className="stat-unit">instrucciones</div>
        </div>
      </div>

      {/* Mapa */}
      {viaje.overviewPolyline && viaje.origen && viaje.destino && (
        <MapaRuta
          encodedPolyline={viaje.overviewPolyline}
          origen={viaje.origen}
          destino={viaje.destino}
        />
      )}

      {/* Predicción climática */}
      {viaje.prediccionLluvia && (
        <AlertaClimatica
          prediccion={viaje.prediccionLluvia}
          alertaNivel={viaje.alertaNivel}
          alertaMensaje={viaje.alertaMensaje}
          factorAjuste={viaje.factorAjuste}
        />
      )}

      {/* Ruta alterna */}
      {viaje.sugerirRutaAlterna && (
        <div className="card fade-up-3" style={{ marginTop: '1rem', borderColor: 'rgba(240,160,74,0.4)' }}>
          <p style={{ color: 'var(--accent2)', fontWeight: 600, marginBottom: '0.35rem' }}>◆ Ruta alterna sugerida</p>
          <p style={{ fontSize: '0.88rem', color: 'var(--muted)', lineHeight: 1.5 }}>{viaje.razonRutaAlterna}</p>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1.75rem', flexWrap: 'wrap' }} className="fade-up-3">
        <Link
          to={`/viaje/${id}/en-ruta`}
          state={{ viaje }}
          className="btn btn-primary"
          style={{ marginTop: 0 }}
        >
          Iniciar navegación →
        </Link>
        <button
          className="btn btn-danger"
          onClick={handleFinalizar}
          disabled={finalizing}
        >
          {finalizing ? <><span className="spinner" /> Finalizando...</> : 'Finalizar viaje'}
        </button>
        <Link to="/" className="btn btn-secondary">← Nuevo viaje</Link>
        <Link to="/historial/1" className="btn btn-secondary">Ver historial</Link>
      </div>
    </div>
  );
}
