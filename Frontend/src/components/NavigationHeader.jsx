import { getManeuvreIcon, formatDistancia } from '../utils/navUtils';

/**
 * Banner superior de instrucción de navegación.
 * Siempre tiene fondo oscuro (HUD) independiente del tema.
 */
export default function NavigationHeader({ paso, distanciaRestante, eta }) {
  if (!paso) return null;

  const icon = getManeuvreIcon(paso.instruccion ?? '');
  const distPaso = formatDistancia(paso.distanciaMetros);
  const distRestante = formatDistancia(distanciaRestante);

  const etaStr = eta
    ? new Date(eta).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div className="nav-instruction-banner">
      <span className="nav-maneuver-icon">{icon}</span>
      <div style={{ flex: 1 }}>
        <div className="nav-instruction-text">
          {paso.instruccion ?? 'Continúa por la ruta'}
        </div>
        <div className="nav-instruction-sub">
          en {distPaso}
          {distRestante && ` · ${distRestante} restantes`}
          {etaStr && ` · Llegada: ${etaStr}`}
        </div>
      </div>
    </div>
  );
}
