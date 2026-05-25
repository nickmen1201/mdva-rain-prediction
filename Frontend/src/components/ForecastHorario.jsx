import { useEffect, useState } from 'react';
import { getWeatherForecast } from '../api/client';

/**
 * Punto 5 del feedback: timeline horario de probabilidad de lluvia.
 *
 * Llama al endpoint /api/weather/forecast (Open-Meteo + ML local) y
 * muestra una fila de barras verticales con la próxima ventana horaria.
 *
 * Color de cada barra según probabilidad:
 *   < 40%  verde   (VERDE)
 *   40-70% amarillo (AMARILLO)
 *   ≥ 70%  rojo    (ROJO)
 *
 * Coherente con la regla de negocio del TripPlannerOrchestrator.
 */
export default function ForecastHorario({
  centro = { lat: 6.2442, lng: -75.5812 },
  horas = 6,
  refreshMs = 600_000,  // 10 min
}) {
  const [data, setData] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const cargar = async () => {
      setCargando(true);
      setError(null);
      try {
        const res = await getWeatherForecast(centro.lat, centro.lng, horas);
        if (!cancelled) setData(res ?? []);
      } catch (err) {
        if (!cancelled) setError('No pudimos cargar el pronóstico del clima. Reintentando en unos minutos...');
        console.error('ForecastHorario: error', err);
      } finally {
        if (!cancelled) setCargando(false);
      }
    };
    cargar();
    const t = setInterval(cargar, refreshMs);
    return () => { cancelled = true; clearInterval(t); };
  }, [centro.lat, centro.lng, horas, refreshMs]);

  const colorPara = (prob) => {
    if (prob >= 0.7) return '#f04a4a'; // rojo
    if (prob >= 0.4) return '#f0c84a'; // amarillo
    return '#4af0a0';                  // verde
  };

  const ahora = new Date();

  return (
    <div style={{
      background: 'rgba(17, 19, 24, 0.9)',
      backdropFilter: 'blur(10px)',
      padding: '12px 16px',
      borderRadius: '10px',
      border: '1px solid var(--border)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      minWidth: '320px',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '10px',
      }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text)' }}>
          ☔ Pronóstico próximas {horas} h
        </span>
        {cargando && <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>⟳</span>}
      </div>

      {error ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{error}</div>
      ) : data.length === 0 && !cargando ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Sin datos</div>
      ) : (
        <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-end', height: '90px' }}>
          {data.map((h, i) => {
            const prob = h.probabilidadRf ?? 0;
            const altura = Math.max(8, prob * 80);
            const esAhora = i === 0 || (new Date(h.timestamp).getHours() === ahora.getHours());
            return (
              <div key={i} style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                flex: 1,
              }} title={`${(prob * 100).toFixed(0)}% lluvia · ${h.temperaturaC?.toFixed(0)}°C`}>
                <span style={{ fontSize: '0.65rem', color: 'var(--text)', fontWeight: 600 }}>
                  {(prob * 100).toFixed(0)}%
                </span>
                <div style={{
                  width: '100%',
                  height: `${altura}px`,
                  background: colorPara(prob),
                  borderRadius: '3px 3px 0 0',
                  border: esAhora ? '2px solid var(--text)' : 'none',
                  transition: 'height 0.4s ease',
                }} />
                <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>
                  {String(h.hora ?? '').padStart(2, '0')}h
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
