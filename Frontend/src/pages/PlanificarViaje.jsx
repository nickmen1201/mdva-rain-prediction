import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { planificarViaje } from '../api/client';
import { useMapsLibrary } from '@vis.gl/react-google-maps';

export default function PlanificarViaje() {
  const navigate = useNavigate();
  const placesLib = useMapsLibrary('places');

  const [idVehiculo, setIdVehiculo] = useState('');
  const [origen, setOrigen] = useState({ lat: null, lng: null, displayName: '' });
  const [destino, setDestino] = useState({ lat: null, lng: null, displayName: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const originInputRef = useRef(null);
  const destInputRef = useRef(null);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!origen.lat || !destino.lat) {
      setError("Por favor seleccione origen y destino de las sugerencias del autocompletado.");
      return;
    }
    setError(null);
    setLoading(true);

    const payload = {
      idVehiculo: idVehiculo || null,
      origen: { lat: origen.lat, lng: origen.lng, displayName: origen.displayName },
      destino: { lat: destino.lat, lng: destino.lng, displayName: destino.displayName },
    };

    try {
      const response = await planificarViaje(payload);
      navigate(`/viaje/${response.idViaje}`, { state: { viaje: response } });
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
    <div style={{ textAlign: "center" }}>
      <h1 className="page-title fade-up">Planificar viaje</h1>
      <p className="page-subtitle fade-up"> Búsqueda rápida con Google Places · Ajuste inteligente</p>

      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          {/* Vehículo */}
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Placa vehículo (opcional)</label>
            <input
              type="text"
              value={idVehiculo}
              onChange={(e) => setIdVehiculo(e.target.value)}
              placeholder="Ej. ABC123"
              maxLength={10}
            />
          </div>

          {/* Origen */}
          <div className="field-section">Origen</div>
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Origen</label>
            <input ref={originInputRef} type="text" placeholder="Ej. UPB, Medellín" />
            {origen.lat && <span style={{ fontSize: '0.75rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ Origen fijado: {origen.displayName}</span>}
          </div>

          {/* Destino */}
          <div className="field-section">Destino</div>
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Buscar Punto de Destino</label>
            <input ref={destInputRef} type="text" placeholder="Ej. EAFIT, Medellín" />
            {destino.lat && <span style={{ fontSize: '0.75rem', color: 'var(--accent)', marginTop: '0.5rem' }}>✓ Destino fijado: {destino.displayName}</span>}
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: '2rem' }}>
          {loading ? <><span className="spinner" /> Calculando ruta...</> : 'Planificar viaje →'}
        </button>
      </form>
    </div>
  );
}