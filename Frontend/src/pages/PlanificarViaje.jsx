import { useState, useRef, useEffect, createRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { planificarViaje } from '../api/client';
import { useMapsLibrary } from '@vis.gl/react-google-maps';

export default function PlanificarViaje() {
  const navigate = useNavigate();
  const placesLib = useMapsLibrary('places');

  const [idVehiculo, setIdVehiculo] = useState('');
  const [origen, setOrigen] = useState({ lat: null, lng: null, displayName: '' });
  const [destino, setDestino] = useState({ lat: null, lng: null, displayName: '' });
  const [paradas, setParadas] = useState([]); // [{ lat, lng, displayName }]
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const originInputRef = useRef(null);
  const destInputRef = useRef(null);
  const paradasRefs = useRef([]);

  // Init origin autocomplete
  useEffect(() => {
    if (!placesLib || !originInputRef.current) return;
    const ac = new placesLib.Autocomplete(originInputRef.current, { fields: ['geometry', 'name', 'formatted_address'] });
    ac.addListener('place_changed', () => {
      const place = ac.getPlace();
      if (place.geometry) {
        setOrigen({ lat: place.geometry.location.lat(), lng: place.geometry.location.lng(), displayName: place.name || place.formatted_address });
      }
    });
  }, [placesLib]);

  // Init dest autocomplete
  useEffect(() => {
    if (!placesLib || !destInputRef.current) return;
    const ac = new placesLib.Autocomplete(destInputRef.current, { fields: ['geometry', 'name', 'formatted_address'] });
    ac.addListener('place_changed', () => {
      const place = ac.getPlace();
      if (place.geometry) {
        setDestino({ lat: place.geometry.location.lat(), lng: place.geometry.location.lng(), displayName: place.name || place.formatted_address });
      }
    });
  }, [placesLib]);


  // Attach autocomplete to waypoints
  useEffect(() => {
    if (!placesLib) return;
    paradas.forEach((parada, i) => {
      const inputEl = paradasRefs.current[i]?.current;
      if (inputEl && !inputEl._hasAutocomplete) {
        inputEl._hasAutocomplete = true;
        const ac = new placesLib.Autocomplete(inputEl, { fields: ['geometry', 'name', 'formatted_address'] });
        ac.addListener('place_changed', () => {
          const place = ac.getPlace();
          if (place.geometry) {
            const loc = {
              lat: place.geometry.location.lat(),
              lng: place.geometry.location.lng(),
              displayName: place.name || place.formatted_address
            };
            setParadas(prev => {
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!origen.lat || !destino.lat) {
      setError("Por favor seleccione origen y destino de las sugerencias.");
      return;
    }
    
    // Filter out empty waypoints
    const validParadas = paradas.filter(p => p.lat && p.lng);

    setError(null);
    setLoading(true);

    const payload = {
      idVehiculo: idVehiculo || null,
      origen: { lat: origen.lat, lng: origen.lng, displayName: origen.displayName },
      destino: { lat: destino.lat, lng: destino.lng, displayName: destino.displayName },
      paradas: validParadas.map(p => ({ lat: p.lat, lng: p.lng, displayName: p.displayName }))
    };

    try {
      const response = await planificarViaje(payload);
      navigate(`/viaje/${response.idViaje}`, {
        state: {
          viaje: response,
          paradas: validParadas
        }
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
    <div className="page-content" style={{ textAlign: "center" }}>
      <h1 className="page-title fade-up">Planificar viaje</h1>
      <p className="page-subtitle fade-up"> Búsqueda rápida con Google Places · Soporte multi-parada</p>

      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          {/* Vehículo */}
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Placa vehículo (opcional)</label>
            <input type="text" value={idVehiculo} onChange={(e) => setIdVehiculo(e.target.value)} placeholder="Ej. ABC123" maxLength={10} />
          </div>

          {/* Origen */}
          <div className="field-section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Origen</span>
            <button 
              type="button" 
              onClick={() => {
                if (!navigator.geolocation) {
                  setError("Tu navegador no soporta geolocalización.");
                  return;
                }
                setLoading(true);
                navigator.geolocation.getCurrentPosition(
                  (pos) => {
                    const lat = pos.coords.latitude;
                    const lng = pos.coords.longitude;
                    setOrigen({ lat, lng, displayName: "Mi ubicación actual" });
                    if (originInputRef.current) originInputRef.current.value = "Mi ubicación actual";
                    setLoading(false);
                  },
                  (err) => {
                    setError("No se pudo obtener tu ubicación. Verifica los permisos de GPS.");
                    setLoading(false);
                  }
                );
              }}
              style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.82rem', padding: '4px 8px' }}
            >
              📍 Usar ubicación actual
            </button>
          </div>
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Origen</label>
            <input ref={originInputRef} type="text" placeholder="Ej. UPB, Medellín" />
            {origen.lat && <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ Origen fijado: {origen.displayName}</span>}
          </div>

          {/* Paradas (Waypoints) */}
          {paradas.map((parada, i) => {
            if (!paradasRefs.current[i]) paradasRefs.current[i] = createRef();
            return (
              <div key={i} className="field" style={{ gridColumn: '1 / -1', borderLeft: '2px solid var(--accent)', paddingLeft: '1rem', marginLeft: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ margin: 0 }}>Parada {i + 1}</label>
                  <button type="button" onClick={() => removeParada(i)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.8rem' }}>✕ Quitar</button>
                </div>
                <input ref={paradasRefs.current[i]} type="text" placeholder="Ej. Centro Comercial" />
                {parada.lat && <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem', display: 'block' }}>✓ Parada fijada: {parada.displayName}</span>}
              </div>
            );
          })}

          <div className="field" style={{ gridColumn: '1 / -1', textAlign: 'left' }}>
            <button type="button" onClick={addParada} className="btn" style={{ background: 'transparent', border: '1px dashed var(--border)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              + Añadir parada intermedia
            </button>
          </div>

          {/* Destino */}
          <div className="field-section">Destino</div>
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Destino</label>
            <input ref={destInputRef} type="text" placeholder="Ej. EAFIT, Medellín" />
            {destino.lat && <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ Destino fijado: {destino.displayName}</span>}
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