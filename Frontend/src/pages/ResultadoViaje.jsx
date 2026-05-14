import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { getViajeById, finalizarViaje, planificarViaje } from '../api/client';
import MapaRuta from '../components/MapaRuta';
import { haversine } from '../utils/navUtils';

const DISTANCIA_MAX_INICIO_M = 1000;

// ── Helpers de presentación ───────────────────────────────────────────────────

function getRainHero(pred) {
  if (!pred) return null;
  if (!pred.llueve) return { icon: '☀️', titulo: 'Sin lluvia prevista', sub: 'Condiciones favorables para tu viaje.' };
  const p = pred.probabilidadRf ?? 0;
  if (p < 0.55) return { icon: '🌦', titulo: 'Posible llovizna', sub: 'Lleva paraguas por si acaso.' };
  if (p < 0.75) return { icon: '🌧', titulo: 'Lluvia moderada', sub: 'Lleva impermeable y maneja con precaución.' };
  return { icon: '⛈', titulo: 'Lluvia fuerte', sub: 'Usa impermeable. Reduce velocidad y aumenta distancia al vehículo de adelante.' };
}

const REC = {
  VERDE:    { icon: '✓', texto: 'Buen momento para salir. Sin lluvia prevista.' },
  AMARILLO: { icon: '🌂', texto: 'Lleva paraguas. Posibles lloviznas en el camino.' },
  ROJO:     { icon: '⚠️', texto: 'Lluvia fuerte. Usa impermeable y conduce despacio.' },
};

const HERO_BORDER = {
  VERDE:    'rgba(74, 240, 160, 0.35)',
  AMARILLO: 'rgba(240, 160, 74, 0.35)',
  ROJO:     'rgba(240, 74,  74, 0.35)',
};

// ── Componente ────────────────────────────────────────────────────────────────

export default function ResultadoViaje() {
  const { id }    = useParams();
  const location  = useLocation();
  const navigate  = useNavigate();

  const [viaje,      setViaje]      = useState(location.state?.viaje ?? null);
  const [loading,    setLoading]    = useState(!viaje);
  const [finalizing, setFinalizing] = useState(false);
  const [starting,   setStarting]   = useState(false);
  const [error,      setError]      = useState(null);
  const [gpsCheck,   setGpsCheck]   = useState('checking');
  const [distOrigen, setDistOrigen] = useState(null);

  const paradas = viaje?.paradasOrdenadas ?? location.state?.paradas ?? [];
  const modoParadas = viaje?.modoParadas ?? location.state?.modoParadas ?? 'ORDEN_INGRESADO';

  useEffect(() => {
    if (viaje) return;
    getViajeById(id)
      .then(setViaje)
      .catch(() => setError('No se pudo cargar el viaje.'))
      .finally(() => setLoading(false));
  }, [id, viaje]);

  useEffect(() => {
    if (!viaje?.origen?.lat || !navigator.geolocation) {
      const timer = setTimeout(() => setGpsCheck('unavailable'), 0);
      return () => clearTimeout(timer);
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const dist = haversine(coords.latitude, coords.longitude, viaje.origen.lat, viaje.origen.lng);
        setDistOrigen(dist);
        setGpsCheck(dist <= DISTANCIA_MAX_INICIO_M ? 'close' : 'far');
      },
      () => setGpsCheck('unavailable'),
      { enableHighAccuracy: false, timeout: 6000, maximumAge: 60000 }
    );
    return undefined;
  }, [viaje]);

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

  const handleIniciarNavegacion = async () => {
    if (!paradas.length) {
      navigate(`/viaje/${id}/en-ruta`, { state: { viaje, paradas: [] } });
      return;
    }

    setStarting(true);
    setError(null);
    try {
      const primeraParada = paradas[0];
      const cola = [...paradas.slice(1), viaje.destino];
      const primerTramo = await planificarViaje({
        idVehiculo: viaje.idVehiculo ?? null,
        origen: viaje.origen,
        destino: primeraParada,
        paradas: [],
        modoParadas: 'ORDEN_INGRESADO',
      });

      navigate(`/viaje/${primerTramo.idViaje}/en-ruta`, {
        state: {
          viaje: primerTramo,
          pendingStops: cola,
          paradas,
          itinerary: [viaje.origen, ...paradas, viaje.destino],
          parentViajeId: viaje.idViaje,
        },
      });
    } catch (err) {
      const msg = err.response?.data?.detail
        ?? err.response?.data?.message
        ?? err.message
        ?? 'No se pudo iniciar la navegación por paradas.';
      setError(msg);
    } finally {
      setStarting(false);
    }
  };

  if (loading) return <div style={{ padding: '3rem', color: 'var(--muted)', fontFamily: 'DM Mono' }}>Cargando viaje...</div>;
  if (error)   return <div className="error-box" style={{ marginTop: '2rem' }}>{error}</div>;
  if (!viaje)  return null;

  // ── Derivaciones de presentación ─────────────────────────────────────────
  const pred       = viaje.prediccionLluvia ?? null;
  const hero       = getRainHero(pred);
  const rec        = REC[viaje.alertaNivel] ?? null;
  const extraMin   = (viaje.tiempoEstimadoMin > 0 && viaje.tiempoBaseMin > 0 && viaje.tiempoEstimadoMin > viaje.tiempoBaseMin)
                       ? viaje.tiempoEstimadoMin - viaje.tiempoBaseMin : 0;
  const distKm     = viaje.distanciaMetros ? (viaje.distanciaMetros / 1000).toFixed(1) : '—';
  const vientoKmh  = pred?.velocidadVientoMs != null ? Math.round(pred.velocidadVientoMs * 3.6) : null;
  const horaStr    = viaje.horaInicio
    ? new Date(viaje.horaInicio).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : '—';
  const heroBorder = HERO_BORDER[viaje.alertaNivel] ?? 'var(--border)';

  return (
    <div className="page-content">

      {/* ── Header ── */}
      <div className="fade-up" style={{ marginBottom: '0.25rem' }}>
        <h1 className="page-title">
          De {viaje.origen?.displayName ?? 'Origen'}<br />
          a {viaje.destino?.displayName ?? 'Destino'}
        </h1>
        <p className="page-subtitle">Viaje #{viaje.idViaje} · {horaStr}</p>
      </div>

      {/* ── Hero clima ── */}
      {hero && (
        <div className="card fade-up" style={{ borderColor: heroBorder, marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ fontSize: '2.6rem', lineHeight: 1, flexShrink: 0 }}>{hero.icon}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text)' }}>{hero.titulo}</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.9rem', marginTop: '0.2rem' }}>{hero.sub}</div>
            </div>
          </div>
          {rec && (
            <div style={{
              marginTop: '0.9rem',
              paddingTop: '0.9rem',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.92rem',
              color: 'var(--text-soft)',
            }}>
              <span style={{ fontSize: '1rem' }}>{rec.icon}</span>
              <span>{rec.texto}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Stats ── */}
      <div className="stats-grid fade-up">
        <div className="stat-item">
          <div className="stat-label">Duración estimada</div>
          <div className="stat-value">{viaje.tiempoEstimadoMin ?? '—'}</div>
          <div className="stat-unit">
            min
            {extraMin > 0 && (
              <span style={{ color: 'var(--accent2)', fontSize: '0.7rem', marginLeft: '0.25rem' }}>
                +{extraMin} por lluvia
              </span>
            )}
          </div>
        </div>

        <div className="stat-item">
          <div className="stat-label">Distancia</div>
          <div className="stat-value">{distKm}</div>
          <div className="stat-unit">km</div>
        </div>

        {viaje.alertaNivel && (
          <div className="stat-item" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div className="stat-label">Condición</div>
            <span className={`alerta-badge alerta-${viaje.alertaNivel}`} style={{ marginTop: '0.4rem', alignSelf: 'flex-start' }}>
              {{ VERDE: '●', AMARILLO: '◆', ROJO: '▲' }[viaje.alertaNivel]} {viaje.alertaNivel}
            </span>
          </div>
        )}
      </div>

      {/* ── Condiciones del momento ── */}
      {pred && (pred.temperaturaC != null || pred.humedadPct != null || vientoKmh != null) && (
        <div className="fade-up" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
          {pred.temperaturaC != null && (
            <span style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: '999px', padding: '0.3rem 0.85rem',
              fontSize: '0.88rem', color: 'var(--text-soft)',
            }}>
              🌡️ {Math.round(pred.temperaturaC)}°C
            </span>
          )}
          {pred.humedadPct != null && (
            <span style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: '999px', padding: '0.3rem 0.85rem',
              fontSize: '0.88rem', color: 'var(--text-soft)',
            }}>
              💧 {Math.round(pred.humedadPct)}% humedad
            </span>
          )}
          {vientoKmh != null && (
            <span style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: '999px', padding: '0.3rem 0.85rem',
              fontSize: '0.88rem', color: 'var(--text-soft)',
            }}>
              💨 {vientoKmh} km/h
            </span>
          )}
        </div>
      )}

      {/* ── Mapa ── */}
      {viaje.overviewPolyline && viaje.origen && viaje.destino && (
        <MapaRuta
          encodedPolyline={viaje.overviewPolyline}
          origen={viaje.origen}
          destino={viaje.destino}
          paradas={paradas}
        />
      )}

      {paradas.length > 0 && (
        <div className="card fade-up-3" style={{ marginTop: '1rem' }}>
          <div className="section-heading">
            Itinerario · {modoParadas === 'OPTIMIZAR_RUTA' ? 'orden optimizado' : 'orden establecido'}
          </div>
          <ol className="itinerary-list">
            <li><span>Origen</span><strong>{viaje.origen?.displayName ?? 'Origen'}</strong></li>
            {paradas.map((parada, index) => (
              <li key={`${parada.lat}-${parada.lng}-${index}`}>
                <span>Parada {index + 1}</span>
                <strong>{parada.displayName ?? `Parada ${index + 1}`}</strong>
              </li>
            ))}
            <li><span>Destino final</span><strong>{viaje.destino?.displayName ?? 'Destino'}</strong></li>
          </ol>
        </div>
      )}

      {/* ── Ruta ajustada ── */}
      {viaje.sugerirRutaAlterna && (
        <div className="card fade-up-3" style={{ marginTop: '1rem', borderColor: 'rgba(240,160,74,0.35)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <span>🔀</span>
            <span style={{ fontWeight: 600, color: 'var(--accent2)' }}>Ajustamos tu ruta</span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--muted)', lineHeight: 1.55, margin: 0 }}>
            Cambiamos el recorrido para reducir tu exposición a la lluvia.
            Llegas a tu destino de forma más segura.
          </p>
        </div>
      )}

      {/* ── Acciones ── */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1.75rem', flexWrap: 'wrap', alignItems: 'flex-start' }} className="fade-up-3">
        <button
          className="btn btn-primary"
          style={{ marginTop: 0 }}
          disabled={starting || gpsCheck === 'checking' || gpsCheck === 'far'}
          onClick={handleIniciarNavegacion}
        >
          {gpsCheck === 'checking'
            ? <><span className="spinner" /> Verificando ubicación...</>
            : 'Iniciar navegación'}
        </button>
        <button className="btn btn-danger" onClick={handleFinalizar} disabled={finalizing}>
          {finalizing ? <><span className="spinner" /> Finalizando...</> : 'Cancelar viaje'}
        </button>
        <Link to="/planificar" className="btn btn-secondary">Nuevo viaje</Link>
        <Link to="/historial/1" className="btn btn-secondary">Ver historial</Link>
      </div>

      {gpsCheck === 'far' && distOrigen != null && (
        <p style={{ marginTop: '1rem', marginBottom: '2rem', fontSize: '0.88rem', color: 'var(--muted)', lineHeight: 1.5 }}>
          Estás a {(distOrigen / 1000).toFixed(1)} km del punto de partida. Acércate para poder iniciar la navegación.
        </p>
      )}

    </div>
  );
}
