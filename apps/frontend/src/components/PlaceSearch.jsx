import { useEffect, useRef, useState } from 'react';
import { searchPlaces, suggestPlaces } from '../api/client';

const DEBOUNCE_MS = 350;

// Búsqueda de lugares del Valle de Aburrá: sugerencias mientras se escribe (Photon/OSM, con espera
// de 350 ms tras la última tecla) y búsqueda completa con Enter o el botón (Nominatim/OSM).
// Flechas ↑/↓ recorren las sugerencias y Enter elige la resaltada.
export default function PlaceSearch({ label, placeholder, selected, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | loading | error
  const [active, setActive] = useState(-1);
  const skipSuggest = useRef(false);

  // Sugerencias con espera tras la última tecla; cancela la petición anterior si llega otra.
  useEffect(() => {
    const q = query.trim();
    if (skipSuggest.current) {
      skipSuggest.current = false;
      return undefined;
    }
    if (q.length < 3) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setStatus('loading');
      try {
        setResults(await suggestPlaces(q, controller.signal));
        setActive(-1);
        setStatus('idle');
      } catch (err) {
        if (err?.name !== 'CanceledError') setStatus('error');
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const buscar = async () => {
    const q = query.trim();
    if (q.length < 3) {
      setResults([]);
      return;
    }
    setStatus('loading');
    try {
      setResults(await searchPlaces(q));
      setActive(-1);
      setStatus('idle');
    } catch {
      setResults(null);
      setStatus('error');
    }
  };

  const elegir = (r) => {
    onSelect({ lat: r.lat, lng: r.lng, displayName: r.displayName.split(',').slice(0, 2).join(',') });
    skipSuggest.current = true;
    setResults(null);
    setActive(-1);
    setQuery('');
  };

  const onKeyDown = (e) => {
    const n = results?.length ?? 0;
    if (e.key === 'ArrowDown' && n > 0) {
      e.preventDefault();
      setActive((i) => (i + 1) % n);
    } else if (e.key === 'ArrowUp' && n > 0) {
      e.preventDefault();
      setActive((i) => (i <= 0 ? n - 1 : i - 1));
    } else if (e.key === 'Escape') {
      setResults(null);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (active >= 0 && active < n) elegir(results[active]);
      else buscar();
    }
  };

  return (
    <div className="field place-search" style={{ gridColumn: '1 / -1' }}>
      {label && <label>{label}</label>}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={query}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={Boolean(results?.length)}
          aria-autocomplete="list"
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.trim().length < 3) {
              setResults(null);
              setStatus('idle');
            }
          }}
          onKeyDown={onKeyDown}
        />
        <button type="button" className="btn btn-secondary" style={{ marginTop: 0 }} onClick={buscar}
                disabled={status === 'loading'}>
          {status === 'loading' ? <span className="spinner" /> : 'Buscar'}
        </button>
      </div>
      {status === 'error' && <span className="field-hint error">No se pudo buscar la dirección. Puedes tocar el mapa.</span>}
      {results && results.length === 0 && status === 'idle' && (
        <span className="field-hint">Sin resultados en el Valle de Aburrá. Prueba con otro nombre o toca el mapa.</span>
      )}
      {results && results.length > 0 && (
        <ul className="place-results" role="listbox">
          {results.map((r, i) => (
            <li key={`${r.lat},${r.lng}`} role="option" aria-selected={i === active}>
              <button type="button" className={i === active ? 'active' : undefined}
                      onMouseDown={(e) => e.preventDefault()} onClick={() => elegir(r)}>
                {r.displayName}
              </button>
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
