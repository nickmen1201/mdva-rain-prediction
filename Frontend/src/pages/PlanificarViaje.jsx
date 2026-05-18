import { useState, useRef, useEffect, createRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { planificarViaje } from '../api/client';
import { Map, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import HeatmapClima from '../components/HeatmapClima';
import ForecastHorario from '../components/ForecastHorario';

const MEDELLIN_CENTRO = { lat: 6.2442, lng: -75.5812 };

// ── Helper: reverse geocoding (lat/lng → dirección) ─────────────────────────
function useReverseGeocoder() {
  const geocodingLib = useMapsLibrary('geocoding');
  const geocoderRef = useRef(null);

  useEffect(() => {
    if (geocodingLib && !geocoderRef.current) {
      geocoderRef.current = new geocodingLib.Geocoder();
    }
  }, [geocodingLib]);

  return useCallback(async (lat, lng) => {
    if (!geocoderRef.current) return null;
    try {
      const { results } = await geocoderRef.current.geocode({ location: { lat, lng } });
      return results?.[0]?.formatted_address ?? null;
    } catch {
      return null;
    }
  }, []);
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

// ── Subcomponente: mapa con pins draggables para origen/destino ─────────────
function MapaSelector({ origen, destino, onMoveOrigen, onMoveDestino }) {
  const map = useMap();
  const markerOrigenRef = useRef(null);
  const markerDestinoRef = useRef(null);

  // Marker de origen
  useEffect(() => {
    if (!map || !window.google) return;
    if (origen.lat == null || origen.lng == null) {
      markerOrigenRef.current?.setMap(null);
      markerOrigenRef.current = null;
      return;
    }
    if (markerOrigenRef.current) {
      markerOrigenRef.current.setPosition({ lat: origen.lat, lng: origen.lng });
    } else {
      markerOrigenRef.current = new window.google.maps.Marker({
        position: { lat: origen.lat, lng: origen.lng },
        map,
        draggable: true,
        title: 'Origen — arrastrame',
        label: { text: 'A', color: '#0a0c10', fontWeight: 'bold' },
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 14,
          fillColor: '#4af0a0',
          fillOpacity: 1,
          strokeColor: '#0a0c10',
          strokeWeight: 2,
        },
      });
      markerOrigenRef.current.addListener('dragend', (e) => {
        onMoveOrigen(e.latLng.lat(), e.latLng.lng());
      });
    }
  }, [map, origen.lat, origen.lng, onMoveOrigen]);

  // Marker de destino
  useEffect(() => {
    if (!map || !window.google) return;
    if (destino.lat == null || destino.lng == null) {
      markerDestinoRef.current?.setMap(null);
      markerDestinoRef.current = null;
      return;
    }
    if (markerDestinoRef.current) {
      markerDestinoRef.current.setPosition({ lat: destino.lat, lng: destino.lng });
    } else {
      markerDestinoRef.current = new window.google.maps.Marker({
        position: { lat: destino.lat, lng: destino.lng },
        map,
        draggable: true,
        title: 'Destino — arrastrame',
        label: { text: 'B', color: '#0a0c10', fontWeight: 'bold' },
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 14,
          fillColor: '#f0a04a',
          fillOpacity: 1,
          strokeColor: '#0a0c10',
          strokeWeight: 2,
        },
      });
      markerDestinoRef.current.addListener('dragend', (e) => {
        onMoveDestino(e.latLng.lat(), e.latLng.lng());
      });
    }
  }, [map, destino.lat, destino.lng, onMoveDestino]);

  // Auto-fit cuando ambos puntos están definidos
  useEffect(() => {
    if (!map || origen.lat == null || destino.lat == null) return;
    const bounds = new window.google.maps.LatLngBounds();
    bounds.extend({ lat: origen.lat, lng: origen.lng });
    bounds.extend({ lat: destino.lat, lng: destino.lng });
    map.fitBounds(bounds, { top: 60, right: 60, bottom: 60, left: 60 });
  }, [map, origen.lat, origen.lng, destino.lat, destino.lng]);

  return null;
}

export default function PlanificarViaje() {
  const navigate = useNavigate();
  const placesLib = useMapsLibrary('places');
  const reverseGeocode = useReverseGeocoder();

  const [idVehiculo, setIdVehiculo] = useState('');
  const [origen, setOrigen] = useState({ lat: null, lng: null, displayName: '' });
  const [destino, setDestino] = useState({ lat: null, lng: null, displayName: '' });
  const [paradas, setParadas] = useState([]); // [{ lat, lng, displayName }]

  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState(null);

  const originInputRef = useRef(null);
  const destInputRef = useRef(null);
  const paradasRefs = useRef([]);

  useEffect(() => {
    if (!placesLib || !originInputRef.current) return;
    const ac = new placesLib.Autocomplete(originInputRef.current, {
      fields: ['geometry', 'name', 'formatted_address'],
    });
    ac.addListener('place_changed', () => {
      const place = ac.getPlace();
      if (place.geometry) {
        setOrigen({
          lat: place.geometry.location.lat(),
          lng: place.geometry.location.lng(),
          displayName: place.name || place.formatted_address,
        });
      }
    });
  }, [placesLib]);

  useEffect(() => {
    if (!placesLib || !destInputRef.current) return;
    const ac = new placesLib.Autocomplete(destInputRef.current, {
      fields: ['geometry', 'name', 'formatted_address'],
    });
    ac.addListener('place_changed', () => {
      const place = ac.getPlace();
      if (place.geometry) {
        setDestino({
          lat: place.geometry.location.lat(),
          lng: place.geometry.location.lng(),
          displayName: place.name || place.formatted_address,
        });
      }
    });
  }, [placesLib]);

  useEffect(() => {
    if (!placesLib) return;
    paradas.forEach((_, i) => {
      const inputEl = paradasRefs.current[i]?.current;
      if (inputEl && !inputEl._hasAutocomplete) {
        inputEl._hasAutocomplete = true;
        const ac = new placesLib.Autocomplete(inputEl, {
          fields: ['geometry', 'name', 'formatted_address'],
        });
        ac.addListener('place_changed', () => {
          const place = ac.getPlace();
          if (place.geometry) {
            const loc = {
              lat: place.geometry.location.lat(),
              lng: place.geometry.location.lng(),
              displayName: place.name || place.formatted_address,
            };
            setParadas((prev) => {
              const updated = [...prev];
              updated[i] = loc;
              return updated;
            });
          }
        });
      }
    });
  }, [placesLib, paradas.length]);

  const addParada = () => setParadas([...paradas, { lat: null, lng: null, displayName: '' }]);

  const removeParada = (i) => {
    paradasRefs.current.splice(i, 1);
    setParadas(paradas.filter((_, idx) => idx !== i));
  };

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
      if (originInputRef.current) originInputRef.current.value = nombre;
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
    if (originInputRef.current && direccion) originInputRef.current.value = direccion;
  }, [reverseGeocode]);

  const handleMoveDestino = useCallback(async (lat, lng) => {
    const direccion = await reverseGeocode(lat, lng);
    setDestino({ lat, lng, displayName: direccion ?? `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
    if (destInputRef.current && direccion) destInputRef.current.value = direccion;
  }, [reverseGeocode]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!origen.lat || !destino.lat) {
      setError('Por favor seleccione origen y destino de las sugerencias.');
      return;
    }

    const validParadas = paradas.filter((p) => p.lat && p.lng);
    setError(null);
    setLoading(true);

    const payload = {
      idVehiculo: idVehiculo || null,
      origen: { lat: origen.lat, lng: origen.lng, displayName: origen.displayName },
      destino: { lat: destino.lat, lng: destino.lng, displayName: destino.displayName },
      paradas: validParadas.map((p) => ({ lat: p.lat, lng: p.lng, displayName: p.displayName })),
      modoParadas: validParadas.length > 0 ? modoParadas : 'ORDEN_INGRESADO',
    };

    try {
      const response = await planificarViaje(payload);
      navigate(`/viaje/${response.idViaje}`, {
        state: {
          viaje: response,
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
      <p className="page-subtitle fade-up">Busqueda rapida con Google Places · Soporte multi-parada</p>

      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Placa vehiculo (opcional)</label>
            <input
              type="text"
              value={idVehiculo}
              onChange={(e) => setIdVehiculo(e.target.value)}
              placeholder="Ej. ABC123"
              maxLength={10}
            />
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

          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Origen</label>
            <input ref={originInputRef} type="text" placeholder="Ej. UPB, Medellín" />
            {origen.lat && <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ {origen.displayName}</span>}
          </div>

          {paradas.map((parada, i) => {
            if (!paradasRefs.current[i]) paradasRefs.current[i] = createRef();
            return (
              <div key={i} className="field" style={{ gridColumn: '1 / -1', borderLeft: '2px solid var(--accent)', paddingLeft: '1rem', marginLeft: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ margin: 0 }}>Parada {i + 1}</label>
                  <button type="button" onClick={() => removeParada(i)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.8rem' }}>
                    Quitar
                  </button>
                </div>
                <input ref={paradasRefs.current[i]} type="text" placeholder="Ej. Centro Comercial Santafe" />
                {parada.lat && (
                  <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem', display: 'block' }}>
                    Parada fijada: {parada.displayName}
                  </span>
                )}
              </div>
            );
          })}

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
                  <span>Google sugiere el mejor orden para reducir vueltas.</span>
                </button>
              </div>
            </div>
          )}

          <div className="field-section">Destino</div>
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Destino</label>
            <input ref={destInputRef} type="text" placeholder="Ej. EAFIT, Medellín" />
            {destino.lat && <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ {destino.displayName}</span>}
          </div>

          {/* Forecast 6h: aparece cuando hay origen para ayudar a decidir cuándo salir */}
          {origen.lat && (
            <div className="field" style={{ gridColumn: '1 / -1' }}>
              <ForecastHorario centro={{ lat: origen.lat, lng: origen.lng }} horas={6} />
            </div>
          )}

          {/* Mapa con pins draggables tipo Uber + capa de lluvia */}
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label style={{ marginBottom: '0.5rem' }}>Mapa — arrastrá los pines para ajustar</label>
            <div style={{
              width: '100%',
              height: '320px',
              borderRadius: '10px',
              overflow: 'hidden',
              border: '1px solid var(--border)',
              position: 'relative',
            }}>
              <Map
                defaultCenter={origen.lat ? { lat: origen.lat, lng: origen.lng } : MEDELLIN_CENTRO}
                defaultZoom={14}
                mapId="mdva-planificar-map"
                colorScheme="DARK"
                gestureHandling="greedy"
                disableDefaultUI={false}
              >
                <MapaSelector
                  origen={origen}
                  destino={destino}
                  onMoveOrigen={handleMoveOrigen}
                  onMoveDestino={handleMoveDestino}
                />
                <HeatmapClima
                  centro={origen.lat ? { lat: origen.lat, lng: origen.lng } : MEDELLIN_CENTRO}
                  size={5}
                  spacing={0.008}
                  visible={true}
                />
              </Map>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.4rem' }}>
              {origen.lat && destino.lat
                ? 'Pin verde (A) = origen · Pin naranja (B) = destino. La nube muestra probabilidad de lluvia.'
                : 'Seleccioná origen y destino con el buscador o el botón GPS para ver los pines.'}
            </p>
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading || locating} style={{ marginTop: '2rem' }}>
          {loading ? <><span className="spinner" /> Calculando ruta...</> : 'Planificar viaje'}
        </button>
      </form>
    </div>
  );
}
