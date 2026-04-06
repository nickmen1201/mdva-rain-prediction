import { Link } from 'react-router-dom';

const NIVEL_ICON = { VERDE: '●', AMARILLO: '◆', ROJO: '▲' };

export default function TarjetaViaje({ viaje }) {
  const fecha = viaje.horaInicio
    ? new Date(viaje.horaInicio).toLocaleString('es-CO', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    : '—';

  const origen  = viaje.nombreOrigen  || `${viaje.latOrigen ?? '?'}, ${viaje.lngOrigen ?? '?'}`;
  const destino = viaje.nombreDestino || `${viaje.latDestino ?? '?'}, ${viaje.lngDestino ?? '?'}`;
  const distKm  = viaje.distanciaMetros ? (viaje.distanciaMetros / 1000).toFixed(1) : null;

  return (
    <Link to={`/viaje/${viaje.idViaje}`} className="viaje-card">
      <div style={{ flex: 1 }}>
        <div className="viaje-route">
          {origen} → {destino}
        </div>
        <div className="viaje-meta">
          {fecha}
          {distKm && <span style={{ marginLeft: '1rem' }}>{distKm} km</span>}
          {viaje.tiempoEstimadoMin && <span style={{ marginLeft: '1rem' }}>{viaje.tiempoEstimadoMin} min</span>}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
        {viaje.finalizado
          ? <span style={{ fontFamily: 'DM Mono', fontSize: '0.72rem', color: 'var(--muted)' }}>COMPLETADO</span>
          : <span style={{ fontFamily: 'DM Mono', fontSize: '0.72rem', color: 'var(--accent)' }}>EN CURSO</span>
        }
      </div>
    </Link>
  );
}
