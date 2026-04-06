import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { planificarViaje } from '../api/client';

const initialPoint = { lat: '', lng: '', displayName: '' };

export default function PlanificarViaje() {
  const navigate = useNavigate();
  const [idUsuario,  setIdUsuario]  = useState('1');
  const [idVehiculo, setIdVehiculo] = useState('');
  const [origen,     setOrigen]     = useState({ ...initialPoint });
  const [destino,    setDestino]    = useState({ ...initialPoint });
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  const updateOrigen  = (k, v) => setOrigen((p)  => ({ ...p, [k]: v }));
  const updateDestino = (k, v) => setDestino((p) => ({ ...p, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const payload = {
      idUsuario: parseInt(idUsuario, 10),
      idVehiculo: idVehiculo || null,
      origen: {
        lat:         parseFloat(origen.lat),
        lng:         parseFloat(origen.lng),
        displayName: origen.displayName || undefined,
      },
      destino: {
        lat:         parseFloat(destino.lat),
        lng:         parseFloat(destino.lng),
        displayName: destino.displayName || undefined,
      },
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

  // Quick-fill buttons for testing
  const fillMedellinItagui = () => {
    setOrigen({ lat: '6.2442', lng: '-75.5812', displayName: 'Medellín Centro' });
    setDestino({ lat: '6.1132', lng: '-75.6145', displayName: 'Itagüí' });
  };

  const fillEnvigadoBello = () => {
    setOrigen({ lat: '6.1719', lng: '-75.5939', displayName: 'Envigado' });
    setDestino({ lat: '6.3329', lng: '-75.5567', displayName: 'Bello' });
  };

  return (
    <div>
      <h1 className="page-title fade-up">Planificar viaje</h1>
      <p className="page-subtitle fade-up">Ruta óptima · Predicción de lluvia · Ajuste inteligente</p>

      {/* Quick fill */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }} className="fade-up">
        <button className="btn btn-secondary" type="button" onClick={fillMedellinItagui}>
          Medellín → Itagüí
        </button>
        <button className="btn btn-secondary" type="button" onClick={fillEnvigadoBello}>
          Envigado → Bello
        </button>
      </div>

      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">

          {/* Usuario / vehículo */}
          <div className="field">
            <label>ID Usuario</label>
            <input
              type="number" min="1" required
              value={idUsuario}
              onChange={(e) => setIdUsuario(e.target.value)}
              placeholder="1"
            />
          </div>
          <div className="field">
            <label>Placa vehículo (opcional)</label>
            <input
              type="text"
              value={idVehiculo}
              onChange={(e) => setIdVehiculo(e.target.value)}
              placeholder="ABC123"
              maxLength={10}
            />
          </div>

          {/* Origen */}
          <div className="field-section">Origen</div>
          <div className="field">
            <label>Nombre</label>
            <input
              type="text"
              value={origen.displayName}
              onChange={(e) => updateOrigen('displayName', e.target.value)}
              placeholder="Medellín Centro"
            />
          </div>
          <div className="field" />
          <div className="field">
            <label>Latitud</label>
            <input
              type="number" step="any" required
              value={origen.lat}
              onChange={(e) => updateOrigen('lat', e.target.value)}
              placeholder="6.2442"
            />
          </div>
          <div className="field">
            <label>Longitud</label>
            <input
              type="number" step="any" required
              value={origen.lng}
              onChange={(e) => updateOrigen('lng', e.target.value)}
              placeholder="-75.5812"
            />
          </div>

          {/* Destino */}
          <div className="field-section">Destino</div>
          <div className="field">
            <label>Nombre</label>
            <input
              type="text"
              value={destino.displayName}
              onChange={(e) => updateDestino('displayName', e.target.value)}
              placeholder="Itagüí"
            />
          </div>
          <div className="field" />
          <div className="field">
            <label>Latitud</label>
            <input
              type="number" step="any" required
              value={destino.lat}
              onChange={(e) => updateDestino('lat', e.target.value)}
              placeholder="6.1132"
            />
          </div>
          <div className="field">
            <label>Longitud</label>
            <input
              type="number" step="any" required
              value={destino.lng}
              onChange={(e) => updateDestino('lng', e.target.value)}
              placeholder="-75.6145"
            />
          </div>

        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? <><span className="spinner" /> Calculando ruta...</> : 'Planificar viaje →'}
        </button>
      </form>
    </div>
  );
}
