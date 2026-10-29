export default function AlertaClimatica({ prediccion, alertaNivel, alertaMensaje, factorAjuste }) {
  const iconos = { VERDE: '●', AMARILLO: '◆', ROJO: '▲' };
  const labels = { VERDE: 'Sin riesgo', AMARILLO: 'Precaución', ROJO: 'Riesgo alto' };

  const rfPct   = prediccion ? Math.round((prediccion.probabilidadRf ?? 0) * 100) : 0;
  const rlPct   = prediccion ? Math.round((prediccion.probabilidadRl ?? 0) * 100) : 0;
  const tempC   = prediccion?.temperaturaC?.toFixed(1) ?? '—';
  const humedad = prediccion?.humedadPct?.toFixed(0) ?? '—';
  const viento  = prediccion?.velocidadVientoMs?.toFixed(1) ?? '—';

  return (
    <div className="card fade-up-2">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <p className="section-heading" style={{ margin: 0 }}>Predicción climática</p>
        {alertaNivel && (
          <span className={`alerta-badge alerta-${alertaNivel}`}>
            {iconos[alertaNivel]} {labels[alertaNivel]}
          </span>
        )}
      </div>

      {alertaMensaje && (
        <p style={{ fontSize: '0.92rem', color: 'var(--muted)', marginBottom: '1rem', lineHeight: 1.5 }}>
          {alertaMensaje}
        </p>
      )}

      <div className="pred-grid">
        <div className="pred-item">
          <div className="pred-label">Random Forest</div>
          <div className="pred-value" style={{ color: rfPct > 70 ? 'var(--danger)' : rfPct > 40 ? 'var(--accent2)' : 'var(--accent)' }}>
            {rfPct}%
          </div>
        </div>
        <div className="pred-item">
          <div className="pred-label">Reg. Logística</div>
          <div className="pred-value" style={{ color: rlPct > 70 ? 'var(--danger)' : rlPct > 40 ? 'var(--accent2)' : 'var(--accent)' }}>
            {rlPct}%
          </div>
        </div>
        <div className="pred-item">
          <div className="pred-label">Temperatura</div>
          <div className="pred-value" style={{ color: 'var(--text)' }}>{tempC}<span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}> °C</span></div>
        </div>
        <div className="pred-item">
          <div className="pred-label">Humedad</div>
          <div className="pred-value" style={{ color: 'var(--text)' }}>{humedad}<span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}> %</span></div>
        </div>
        <div className="pred-item">
          <div className="pred-label">Viento</div>
          <div className="pred-value" style={{ color: 'var(--text)' }}>{viento}<span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}> m/s</span></div>
        </div>
        {factorAjuste && (
          <div className="pred-item">
            <div className="pred-label">Factor ajuste</div>
            <div className="pred-value" style={{ color: factorAjuste > 1 ? 'var(--accent2)' : 'var(--accent)' }}>×{factorAjuste.toFixed(2)}</div>
          </div>
        )}
      </div>
    </div>
  );
}
