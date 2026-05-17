import { useState, useRef, useEffect, createRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMapsLibrary } from '@vis.gl/react-google-maps';
import { planificarViaje } from '../api/client';

export default function PlanificarViaje() {
  const navigate = useNavigate();
  const placesLib = useMapsLibrary('places');

  const [idVehiculo, setIdVehiculo] = useState('');
  const [origen, setOrigen] = useState({ lat: null, lng: null, displayName: '' });
  const [destino, setDestino] = useState({ lat: null, lng: null, displayName: '' });
  const [paradas, setParadas] = useState([]);
  const [modoParadas, setModoParadas] = useState('ORDEN_INGRESADO');
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
  }, [placesLib, paradas]);

  const addParada = () => setParadas([...paradas, { lat: null, lng: null, displayName: '' }]);

  const removeParada = (i) => {
    paradasRefs.current.splice(i, 1);
    setParadas(paradas.filter((_, idx) => idx !== i));
  };

  const requestCurrentLocation = () => {
    setError(null);

    if (!navigator.geolocation) {
      setError('Tu navegador no soporta geolocalizacion.');
      return;
    }

    if (!window.isSecureContext) {
      setError('El GPS del telefono requiere abrir la app por HTTPS. En HTTP por IP local el navegador bloquea el permiso sin mostrar la pregunta.');
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setOrigen({ lat, lng, displayName: 'Mi ubicacion actual' });
        if (originInputRef.current) originInputRef.current.value = 'Mi ubicacion actual';
        setLocating(false);
      },
      (geoError) => {
        setError(
          geoError.code === geoError.PERMISSION_DENIED
            ? 'Permiso de GPS denegado. Activalo en los permisos del navegador para este sitio.'
            : 'No se pudo obtener tu ubicacion. Verifica que el GPS este activo e intenta de nuevo.'
        );
        setLocating(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 30000,
      }
    );
  };

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
              onClick={requestCurrentLocation}
              disabled={locating}
              style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.82rem', padding: '4px 8px' }}
            >
              {locating ? 'Solicitando GPS...' : 'Usar ubicacion actual'}
            </button>
          </div>

          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar punto de origen</label>
            <input ref={originInputRef} type="text" placeholder="Ej. UPB, Medellin" />
            {origen.lat && (
              <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>
                Origen fijado: {origen.displayName}
              </span>
            )}
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
            <label>Buscar punto de destino</label>
            <input ref={destInputRef} type="text" placeholder="Ej. EAFIT, Medellin" />
            {destino.lat && (
              <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>
                Destino fijado: {destino.displayName}
              </span>
            )}
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
