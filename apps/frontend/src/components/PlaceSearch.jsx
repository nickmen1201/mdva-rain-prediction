import { useState } from 'react';
import { searchPlaces } from '../api/client';

// Búsqueda de lugares al enviar el texto (Enter o botón), con hasta 5 resultados del Valle de Aburrá.
// Reemplaza el autocompletado de Google Places (spec 011): Nominatim no permite consultas por tecla.
export default function PlaceSearch({ label, placeholder, selected, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | loading | error

  const buscar = async () => {
    const q = query.trim();
    if (q.length < 3) {
      setResults([]);
      return;
    }
    setStatus('loading');
    try {
      setResults(await searchPlaces(q));
      setStatus('idle');
    } catch {
      setResults(null);
      setStatus('error');
    }
  };

  const elegir = (r) => {
    onSelect({ lat: r.lat, lng: r.lng, displayName: r.displayName.split(',').slice(0, 2).join(',') });
    setResults(null);
    setQuery('');
  };

  return (
    <div className="field place-search" style={{ gridColumn: '1 / -1' }}>
      {label && <label>{label}</label>}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={query}
          placeholder={placeholder}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              buscar();
            }
          }}
        />
        <button type="button" className="btn btn-secondary" style={{ marginTop: 0 }} onClick={buscar}
                disabled={status === 'loading'}>
          {status === 'loading' ? <span className="spinner" /> : 'Buscar'}
        </button>
      </div>
      {status === 'error' && <span className="field-hint error">No se pudo buscar la dirección. Puedes tocar el mapa.</span>}
      {results && results.length === 0 && status === 'idle' && (
        <span className="field-hint">Sin resultados en el Valle de Aburrá (escribe al menos 3 letras).</span>
      )}
      {results && results.length > 0 && (
        <ul className="place-results" role="listbox">
          {results.map((r) => (
            <li key={`${r.lat},${r.lng}`}>
              <button type="button" onClick={() => elegir(r)}>{r.displayName}</button>
            </li>
          ))}
        </ul>
      )}
      {selected?.lat != null && (
        <span style={{ fontSize: '0.82rem', color: 'var(--accent)', marginTop: '0.5rem', display: 'block' }}>
          ✓ {selected.displayName}
        </span>
      )}
    </div>
  );
}
