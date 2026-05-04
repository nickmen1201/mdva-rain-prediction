import { useEffect } from 'react';

const CONFIG = {
  INFORMATIVA: { cls: 'toast',     bg: 'rgba(8,10,14,0.96)', border: 'rgba(74,240,160,0.4)', color: '#4af0a0',  icon: 'ℹ', autoDismiss: 6000 },
  PRECAUCION:  { cls: 'banner',    bg: 'rgba(240,160,74,0.92)', border: null, color: '#1a1200',  icon: '⚠', autoDismiss: null },
  PELIGRO:     { cls: 'modal',     bg: null, border: null, color: null, icon: '⚠', autoDismiss: null },
  CRISIS:      { cls: 'crisis',    bg: null, border: null, color: null, icon: '⚠', autoDismiss: null },
};

export default function RecomendacionBanner({ alerta, onCerrar }) {
  if (!alerta) return null;

  const cfg = CONFIG[alerta.nivelSeveridad] ?? CONFIG.INFORMATIVA;

  // Vibrate on crisis
  useEffect(() => {
    if (alerta.nivelSeveridad === 'CRISIS' && navigator.vibrate) {
      navigator.vibrate([600, 200, 600, 200, 600]);
    }
    if (cfg.autoDismiss) {
      const t = setTimeout(onCerrar, cfg.autoDismiss);
      return () => clearTimeout(t);
    }
  }, [alerta, cfg.autoDismiss, onCerrar]);

  // ── INFORMATIVA: floating toast ──────────────────────────────────────────
  if (cfg.cls === 'toast') {
    return (
      <div className="recomendacion-toast" style={{ borderColor: cfg.border, color: cfg.color }}>
        <span>{cfg.icon}</span>
        <span>{alerta.mensaje}</span>
        <button onClick={onCerrar} style={{ background: 'none', border: 'none', color: cfg.color, cursor: 'pointer', marginLeft: '0.5rem', fontSize: '1rem' }}>✕</button>
      </div>
    );
  }

  // ── PRECAUCION: persistent top banner ───────────────────────────────────
  if (cfg.cls === 'banner') {
    return (
      <div className="recomendacion-banner precaucion">
        <span style={{ fontSize: '1.4rem' }}>{cfg.icon}</span>
        <span style={{ flex: 1 }}>{alerta.mensaje}</span>
        <button onClick={onCerrar} style={{ background: 'none', border: '1px solid rgba(0,0,0,0.3)', color: '#1a1200', cursor: 'pointer', padding: '0.35rem 0.85rem', borderRadius: '4px', fontSize: '0.88rem' }}>
          Entendido
        </button>
      </div>
    );
  }

  // ── PELIGRO: modal overlay ───────────────────────────────────────────────
  if (cfg.cls === 'modal') {
    return (
      <div className="recomendacion-modal-overlay">
        <div className="recomendacion-modal-card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>{cfg.icon}</div>
          <h2 style={{ color: '#f0a04a', fontWeight: 800, marginBottom: '0.75rem', fontSize: '1.4rem' }}>
            {alerta.mensaje}
          </h2>
          {alerta.detalleRecomendacion && (
            <p style={{ color: '#c0c4d0', fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '1.5rem' }}>
              {alerta.detalleRecomendacion}
            </p>
          )}
          <button className="btn btn-danger" onClick={onCerrar} style={{ width: '100%' }}>
            Entendido — continuar
          </button>
        </div>
      </div>
    );
  }

  // ── CRISIS: full-screen ──────────────────────────────────────────────────
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
        >
          Deteniéndome en lugar seguro
        </button>
      </div>
    </div>
  );
}
