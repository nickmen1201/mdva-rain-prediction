import { getManeuvreIcon, formatDistancia } from '../utils/navUtils';

/**
 * Panel lateral colapsable con la lista completa de pasos del viaje.
 * Siempre oscuro (HUD). Clic en un paso emite onStepClick(index).
 */
export default function NavigationPanel({ pasos = [], pasoActivo = 0, visible, onClose }) {
  if (!visible) return null;

  return (
    <div className="steps-panel">
      {/* Header */}
      <div style={{
        padding: '0.85rem 1rem',
        borderBottom: '1px solid rgba(74,240,160,0.15)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ color: '#4af0a0', fontFamily: 'DM Mono, monospace', fontSize: '0.78rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Pasos de ruta
        </span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: '#5a6070', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}
          aria-label="Cerrar panel"
        >
          ✕
        </button>
      </div>

      {/* Steps list */}
      <div>
        {pasos.map((paso, i) => (
          <div key={i} className={`step-item${i === pasoActivo ? ' active' : ''}`}>
            <div className="step-number">{i + 1}</div>
            <div>
              <div className="step-text">
                {getManeuvreIcon(paso.instruccion ?? '')} {paso.instruccion ?? '—'}
              </div>
              <div className="step-meta">
                {formatDistancia(paso.distanciaMetros)}
                {paso.duracionSegundos != null && ` · ${Math.round(paso.duracionSegundos / 60)} min`}
              </div>
            </div>
          </div>
        ))}
        {!pasos.length && (
          <div style={{ padding: '1.5rem 1rem', color: '#5a6070', fontFamily: 'DM Mono, monospace', fontSize: '0.88rem' }}>
            No hay pasos disponibles.
          </div>
        )}
      </div>
    </div>
  );
}
