import maplibregl from 'maplibre-gl';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { planificarViaje, reversePlace } from '../api/client';
import ForecastHorario from '../components/ForecastHorario';
import PlaceSearch from '../components/PlaceSearch';
import WeatherHeatmapLayer from '../components/WeatherHeatmapLayer';
import useWeatherGrid from '../hooks/useWeatherGrid';
import { boundsOf } from '../map/geo';
import MapView, { useMap } from '../map/MapView';

const MEDELLIN_CENTRO = { lat: 6.2442, lng: -75.5812 };

// ── Helper: reverse geocoding (lat/lng → dirección) con Nominatim vía Backend ─
async function reverseGeocode(lat, lng) {
  try {
    const r = await reversePlace(lat, lng);
    return r?.displayName?.split(',').slice(0, 2).join(',') ?? null;
  } catch {
    return null;
  }
}

// ── Helper: GPS con retry y diagnóstico vía Permissions API ─────────────────
async function obtenerUbicacion() {
  if (!navigator.geolocation) {
    throw new Error('NO_GEOLOCATION');
  }

  // Si la Permissions API está disponible, consultamos PRIMERO el estado del
  // permiso para el sitio. Esto distingue "bloqueado por el usuario" de
  // "fallo técnico" — Chrome devuelve code=1 en ambos casos sin distinguir.
  if (navigator.permissions?.query) {
    try {
      const perm = await navigator.permissions.query({ name: 'geolocation' });
      if (perm.state === 'denied') {
        const e = new Error('PERMISSION_BLOCKED_FOR_SITE');
        e.code = 1;
        throw e;
      }
    } catch (err) {
      // Si la Permissions API misma falla, seguimos con getCurrentPosition
      if (err.message === 'PERMISSION_BLOCKED_FOR_SITE') throw err;
    }
  }

  return new Promise((resolve, reject) => {
    // 1er intento: alta precisión, 15s, sin cache
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(pos),
      (err1) => {
        // Si fue rechazo de permiso, no tiene sentido reintentar
        if (err1.code === 1) {
          reject(err1);
          return;
        }
        // 2do intento: baja precisión, 10s, permite cache de 1 min
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve(pos),
          (err2) => reject(err2),
          { timeout: 10000, enableHighAccuracy: false, maximumAge: 60_000 }
        );
      },
      { timeout: 15000, enableHighAccuracy: true, maximumAge: 0 }
    );
  });
}

// ── Subcomponente: mapa con pins arrastrables para origen/destino ───────────
function pin(label, color) {
  const el = document.createElement('div');
  el.textContent = label;
  Object.assign(el.style, {
    width: '28px', height: '28px', borderRadius: '50%', background: color, color: '#0a0c10',
    border: '2px solid #0a0c10', display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: '700', cursor: 'grab',
  });
  return el;
}

function useDraggablePin(map, point, label, color, title, onMove) {
  const markerRef = useRef(null);
  const onMoveRef = useRef(onMove);
  useEffect(() => {
    onMoveRef.current = onMove;
  }, [onMove]);

  useEffect(() => {
    if (!map) return;
    if (point.lat == null || point.lng == null) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    if (!markerRef.current) {
      const el = pin(label, color);
      el.title = title;
      markerRef.current = new maplibregl.Marker({ element: el, draggable: true })
        .setLngLat([point.lng, point.lat])
        .addTo(map);
      markerRef.current.on('dragend', () => {
        const { lat, lng } = markerRef.current.getLngLat();
        onMoveRef.current(lat, lng);
      });
    } else {
      markerRef.current.setLngLat([point.lng, point.lat]);
    }
  }, [map, point.lat, point.lng, label, color, title]);

  useEffect(() => () => markerRef.current?.remove(), []);
}

function MapaSelector({ origen, destino, onMoveOrigen, onMoveDestino }) {
  const map = useMap();
  useDraggablePin(map, origen, 'A', '#4af0a0', 'Origen — arrástrame', onMoveOrigen);
  useDraggablePin(map, destino, 'B', '#f0a04a', 'Destino — arrástrame', onMoveDestino);

  // Auto-encuadre cuando ambos puntos están definidos
  useEffect(() => {
    if (!map || origen.lat == null || destino.lat == null) return;
    map.fitBounds(boundsOf([origen, destino]), { padding: 60, duration: 0, maxZoom: 15 });
  }, [map, origen, destino]);

  return null;
}

export default function PlanificarViaje() {
  const navigate = useNavigate();

  const [idVehiculo, setIdVehiculo] = useState('');
  const [tipoVehiculo, setTipoVehiculo] = useState('CARRO');
  const [origen, setOrigen] = useState({ lat: null, lng: null, displayName: '' });
  const [destino, setDestino] = useState({ lat: null, lng: null, displayName: '' });
  const [paradas, setParadas] = useState([]); // [{ lat, lng, displayName }]
  const [modoParadas, setModoParadas] = useState('ORDEN_INGRESADO');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const heatmapCenter = { lat: 6.266, lng: -75.570 };
  const { points: heatmapPoints, error: heatmapError } = useWeatherGrid({
    enabled: true,
    center: heatmapCenter,
    gridSize: 9,
    spacingKm: 5,
  });

  const addParada = () => setParadas([...paradas, { lat: null, lng: null, displayName: '' }]);

  const removeParada = (i) => setParadas(paradas.filter((_, idx) => idx !== i));

  const setParada = (i, loc) => setParadas((prev) => prev.map((p, idx) => (idx === i ? loc : p)));

  // Handler GPS con retry + reverse geocoding
  const handleUsarUbicacionActual = async () => {
    setLoading(true);
    setError(null);
    try {
      const pos = await obtenerUbicacion();
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      // Intenta resolver dirección humana
      const direccion = await reverseGeocode(lat, lng);
      const nombre = direccion ?? 'Mi ubicación actual';
      setOrigen({ lat, lng, displayName: nombre });
    } catch (err) {
      const code = err?.code;
      if (err?.message === 'NO_GEOLOCATION') {
        setError('Tu navegador no soporta geolocalización.');
      } else if (err?.message === 'PERMISSION_BLOCKED_FOR_SITE') {
        setError('Este sitio tiene la ubicación BLOQUEADA en Chrome (aunque el GPS del sistema esté activo). Click en el candado al lado de la URL → Ubicación → Permitir → recargar la página.');
      } else if (code === 1) {
        setError('Permiso de ubicación denegado. Click en el candado al lado de la URL y permití "Ubicación" para este sitio.');
      } else if (code === 2) {
        setError('El GPS no pudo determinar tu ubicación (sin señal). Probá moverte cerca de una ventana o ingresá el origen manualmente.');
      } else if (code === 3) {
        setError('El GPS tardó demasiado en responder. Probá ingresar el origen manualmente.');
      } else {
        setError('No se pudo obtener tu ubicación. Detalle técnico: ' + (err?.message ?? 'desconocido'));
      }
      console.error('GPS error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handlers para mover pins en el mapa
  const handleMoveOrigen = useCallback(async (lat, lng) => {
    const direccion = await reverseGeocode(lat, lng);
    setOrigen({ lat, lng, displayName: direccion ?? `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
  }, []);

  const handleMoveDestino = useCallback(async (lat, lng) => {
    const direccion = await reverseGeocode(lat, lng);
    setDestino({ lat, lng, displayName: direccion ?? `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
  }, []);

  // Tocar el mapa fija el primer punto que falte (origen, luego destino)
  const handleMapClick = useCallback(({ lat, lng }) => {
    if (origen.lat == null) handleMoveOrigen(lat, lng);
    else if (destino.lat == null) handleMoveDestino(lat, lng);
  }, [origen.lat, destino.lat, handleMoveOrigen, handleMoveDestino]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!origen.lat || !destino.lat) {
      setError('Por favor elija origen y destino (búsqueda, GPS o tocando el mapa).');
      return;
    }

    const validParadas = paradas.filter((p) => p.lat && p.lng);
    setError(null);
    setLoading(true);

    const payload = {
      idVehiculo: idVehiculo || null,
      tipoVehiculo,
      origen: { lat: origen.lat, lng: origen.lng, displayName: origen.displayName },
      destino: { lat: destino.lat, lng: destino.lng, displayName: destino.displayName },
      paradas: validParadas.map((p) => ({ lat: p.lat, lng: p.lng, displayName: p.displayName })),
      modoParadas: validParadas.length > 0 ? modoParadas : 'ORDEN_INGRESADO',
    };

    try {
      const response = await planificarViaje(payload);
      const viajePlanificado = {
        ...response,
        idVehiculo: payload.idVehiculo,
        tipoVehiculo,
      };
      navigate(`/viaje/${response.idViaje}`, {
        state: {
          viaje: viajePlanificado,
          idVehiculo: payload.idVehiculo,
          tipoVehiculo,
          paradas: response.paradasOrdenadas?.length ? response.paradasOrdenadas : validParadas,
          modoParadas: response.modoParadas ?? payload.modoParadas,
        },
      });
    } catch (err) {
      const msg = err.response?.data?.detail
        ?? err.response?.data?.message
        ?? err.message
        ?? 'Error al planificar el viaje';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-content" style={{ textAlign: 'center' }}>
      <h1 className="page-title fade-up">Planificar viaje</h1>
      <p className="page-subtitle fade-up">Búsqueda de direcciones con OpenStreetMap · Soporte multi-parada</p>

      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Placa vehiculo (opcional)</label>
            <input
              type="text"
              value={idVehiculo}
              onChange={(e) => setIdVehiculo(e.target.value.toUpperCase())}
              placeholder="Ej. ABC123"
              maxLength={10}
              autoCapitalize="characters"
              style={{ textTransform: 'uppercase' }}
            />
          </div>

          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Tipo de vehiculo</label>
            <div className="route-mode-options vehicle-mode-options">
              {[
                {
                  id: 'CARRO',
                  label: 'Carro',
                  icon: (
                    <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="11" width="20" height="6" rx="1" />
                      <path d="M5 11l2-4h10l2 4" />
                      <circle cx="6.5" cy="17" r="1.5" />
                      <circle cx="17.5" cy="17" r="1.5" />
                    </svg>
                  ),
                },
                {
                  id: 'MOTO',
                  label: 'Moto',
                  icon: (
                    <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="5" cy="16" r="3" />
                      <circle cx="19" cy="16" r="3" />
                      <path d="M8 16l2-5h4l4 5" />
                      <path d="M14 11l2-3h3" />
                    </svg>
                  ),
                },
                {
                  id: 'BICICLETA',
                  label: 'Bicicleta',
                  icon: (
                    <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="5" cy="16" r="3" />
                      <circle cx="19" cy="16" r="3" />
                      <path d="M5 16l4-7 3 7 5-7" />
                      <path d="M17 9l2 7" />
                      <path d="M15 7h4" />
                      <path d="M7 9h4" />
                    </svg>
                  ),
                },
              ].map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className={`route-mode-option${tipoVehiculo === v.id ? ' active' : ''}`}
                  style={{ alignItems: 'center', justifyContent: 'center', minHeight: '88px', gap: '0.5rem' }}
                  onClick={() => setTipoVehiculo(v.id)}
                >
                  {v.icon}
                  <strong style={{ fontSize: '0.9rem', letterSpacing: '0.04em' }}>{v.label}</strong>
                </button>
              ))}
            </div>
          </div>

          <div className="field-section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Origen</span>
            <button
              type="button"
              onClick={handleUsarUbicacionActual}
              disabled={loading}
              aria-label="Usar mi ubicación actual del GPS como origen"
              title="Detectar ubicación con GPS"
              style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.82rem', padding: '4px 8px' }}
            >
              {loading ? <><span className="spinner" /> Detectando...</> : '📍 Usar ubicación actual'}
            </button>
          </div>

          <PlaceSearch label="Buscar punto de origen" placeholder="Ej. Parque Explora" selected={origen} onSelect={setOrigen} />

          {paradas.map((parada, i) => (
            <div key={i} style={{ gridColumn: '1 / -1', borderLeft: '2px solid var(--accent)', paddingLeft: '1rem', marginLeft: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '0.85rem' }}>Parada {i + 1}</strong>
                <button type="button" onClick={() => removeParada(i)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.8rem' }}>
                  Quitar
                </button>
              </div>
              <PlaceSearch placeholder="Ej. Centro Comercial Santafé" selected={parada} onSelect={(loc) => setParada(i, loc)} />
            </div>
          ))}

          <div className="field" style={{ gridColumn: '1 / -1', textAlign: 'left' }}>
            <button type="button" onClick={addParada} className="btn" style={{ background: 'transparent', border: '1px dashed var(--border)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              + Anadir parada intermedia
            </button>
          </div>

          {paradas.length > 0 && (
            <div className="field" style={{ gridColumn: '1 / -1', textAlign: 'left' }}>
              <label>Orden de paradas</label>
              <div className="route-mode-options">
                <button
                  type="button"
                  className={`route-mode-option${modoParadas === 'ORDEN_INGRESADO' ? ' active' : ''}`}
                  onClick={() => setModoParadas('ORDEN_INGRESADO')}
                >
                  <strong>Orden establecido</strong>
                  <span>Hacer las paradas tal como las ingresaste.</span>
                </button>
                <button
                  type="button"
                  className={`route-mode-option${modoParadas === 'OPTIMIZAR_RUTA' ? ' active' : ''}`}
                  onClick={() => setModoParadas('OPTIMIZAR_RUTA')}
                >
                  <strong>Optimizar ruta</strong>
                  <span>Ordena las paradas para recorrer la menor distancia.</span>
                </button>
              </div>
            </div>
          )}

          <div className="field-section">Destino</div>
          <PlaceSearch label="Buscar punto de destino" placeholder="Ej. Estadio Atanasio Girardot" selected={destino} onSelect={setDestino} />

          {/* Forecast 6h: aparece cuando hay origen para ayudar a decidir cuándo salir */}
          {origen.lat && (
            <div className="field" style={{ gridColumn: '1 / -1' }}>
              <ForecastHorario centro={{ lat: origen.lat, lng: origen.lng }} horas={6} />
            </div>
          )}

          {/* Mapa con pins draggables tipo Uber + capa de lluvia */}
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label style={{ marginBottom: '0.5rem' }}>Mapa — toca para fijar puntos y arrastra los pines para ajustar</label>
            <div style={{
              width: '100%',
              height: '320px',
              borderRadius: '10px',
              overflow: 'hidden',
              border: '1px solid var(--border)',
              position: 'relative',
            }}>
              <MapView center={origen.lat ? { lat: origen.lat, lng: origen.lng } : MEDELLIN_CENTRO} zoom={13}
                       onClick={handleMapClick}>
                <MapaSelector
                  origen={origen}
                  destino={destino}
                  onMoveOrigen={handleMoveOrigen}
                  onMoveDestino={handleMoveDestino}
                />
                <WeatherHeatmapLayer
                  points={heatmapPoints}
                  visible={!heatmapError}
                  opacity={0.58}
                />
              </MapView>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.4rem' }}>
              {origen.lat && destino.lat
                ? 'Pin verde (A) = origen · Pin naranja (B) = destino. La nube muestra probabilidad de lluvia.'
                : 'Elige origen y destino con el buscador, el GPS o tocando el mapa.'}
            </p>
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: '2rem' }}>
          {loading ? <><span className="spinner" /> Calculando ruta...</> : 'Planificar viaje'}
        </button>
      </form>
    </div>
  );
}
