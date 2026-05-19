import { useEffect } from 'react';

const CONFIG = {
  INFORMATIVA: { cls: 'toast', border: 'rgba(74,240,160,0.4)', color: '#4af0a0', icon: 'i', autoDismiss: 6000 },
  PRECAUCION: { cls: 'toast', border: 'rgba(240,160,74,0.65)', color: '#f0a04a', icon: '!', autoDismiss: 7500 },
  PELIGRO: { cls: 'toast', border: 'rgba(240,74,74,0.68)', color: '#f04a4a', icon: '!', autoDismiss: 9000 },
  CRISIS: { cls: 'crisis', border: null, color: null, icon: '!', autoDismiss: null },
};

export default function RecomendacionBanner({ alerta, onCerrar }) {
  const cfg = alerta ? (CONFIG[alerta.nivelSeveridad] ?? CONFIG.INFORMATIVA) : CONFIG.INFORMATIVA;

  useEffect(() => {
    if (!alerta) return undefined;

    if (alerta.nivelSeveridad === 'CRISIS' && navigator.vibrate) {
      navigator.vibrate([600, 200, 600, 200, 600]);
    }

    if (cfg.autoDismiss) {
      const timer = setTimeout(onCerrar, cfg.autoDismiss);
      return () => clearTimeout(timer);
    }

    return undefined;
  }, [alerta, cfg.autoDismiss, onCerrar]);

  if (!alerta) return null;

  if (cfg.cls === 'toast') {
    return (
      <div
        className={`recomendacion-toast ${alerta.nivelSeveridad?.toLowerCase() ?? ''}`}
        style={{ borderColor: cfg.border, color: cfg.color }}
        role="status"
      >
        <span className="recomendacion-toast-icon">{cfg.icon}</span>
        <span className="recomendacion-toast-body">
          <strong>{alerta.mensaje}</strong>
          {alerta.detalleRecomendacion && <small>{alerta.detalleRecomendacion}</small>}
        </span>
        <button
          className="recomendacion-toast-close"
          onClick={onCerrar}
          aria-label="Cerrar recomendacion"
          type="button"
        >
          x
        </button>
      </div>
    );
  }

  return (
    <div className="recomendacion-modal-overlay crisis">
      <div className="recomendacion-modal-card crisis" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1.25rem' }}>{cfg.icon}</div>
        <h2 style={{ color: '#f04a4a', fontWeight: 800, fontSize: '1.7rem', marginBottom: '0.75rem', lineHeight: 1.1 }}>
          {alerta.mensaje}
        </h2>
        {alerta.detalleRecomendacion && (
          <p style={{ color: '#e0b0b0', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '2rem' }}>
            {alerta.detalleRecomendacion}
          </p>
        )}
        <button
          className="btn"
          onClick={onCerrar}
          style={{ background: '#f04a4a', color: 'white', width: '100%', padding: '1rem', fontSize: '1.05rem' }}
          type="button"
        >
          Deteniendome en lugar seguro
        </button>
      </div>
    </div>
  );
}
