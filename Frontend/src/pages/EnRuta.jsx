import { useEffect, useRef, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Map, useMap } from '@vis.gl/react-google-maps';
import { getViajeById, finalizarViaje } from '../api/client';

function CapaRuta({ viaje, posicion }) {
  const map = useMap();
  const marcadorGPS = useRef(null);

  useEffect(() => {
    if (!map || !viaje?.overviewPolyline) return;

    const path = window.google.maps.geometry.encoding.decodePath(viaje.overviewPolyline);
    const polyline = new window.google.maps.Polyline({
      path,
      strokeColor: '#4af0a0',
      strokeOpacity: 0.85,
      strokeWeight: 4,
      map,
    });

    const bounds = new window.google.maps.LatLngBounds();
    path.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, { top: 60, right: 40, bottom: 160, left: 40 });

    new window.google.maps.Marker({
      position: { lat: viaje.origen.lat, lng: viaje.origen.lng },
      map,
      icon: { path: window.google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#4af0a0', fillOpacity: 1, strokeColor: '#0a0c10', strokeWeight: 2 },
    });
    new window.google.maps.Marker({
      position: { lat: viaje.destino.lat, lng: viaje.destino.lng },
      map,
      icon: { path: window.google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#f0a04a', fillOpacity: 1, strokeColor: '#0a0c10', strokeWeight: 2 },
    });

    return () => polyline.setMap(null);
  }, [map, viaje]);

  useEffect(() => {
    if (!map || !posicion) return;

    if (marcadorGPS.current) {
      marcadorGPS.current.setPosition(posicion);
    } else {
      marcadorGPS.current = new window.google.maps.Marker({
        position: posicion,
        map,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 10,
          fillColor: '#4af0a0',
          fillOpacity: 0.9,
          strokeColor: '#fff',
          strokeWeight: 3,
        },
        title: 'Tu posición',
        zIndex: 10,
      });
    }
  }, [map, posicion]);

  return null;
}

export default function EnRuta() {
  const { id } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [viaje, setViaje] = useState(state?.viaje ?? null);
  const [posicion, setPosicion] = useState(null);
  const [error, setError] = useState(null);
  const [finalizando, setFinalizando] = useState(false);
  const watchId = useRef(null);

  useEffect(() => {
    if (!viaje) {
      getViajeById(id).then(setViaje).catch(() => setError('No se pudo cargar el viaje.'));
    }
  }, [id, viaje]);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Este navegador no soporta GPS.');
      return;
    }
    watchId.current = navigator.geolocation.watchPosition(
      ({ coords }) => setPosicion({ lat: coords.latitude, lng: coords.longitude }),
      () => setError('No se pudo obtener tu ubicación. Verifica los permisos de GPS.'),
      { enableHighAccuracy: true, maximumAge: 5000 },
    );
    return () => navigator.geolocation.clearWatch(watchId.current);
  }, []);

  const handleFinalizar = async () => {
    setFinalizando(true);
    try {
      await finalizarViaje(id);
    } catch (err) {
      if (err.response?.status !== 409) {
        setError('Error al finalizar el viaje.');
        setFinalizando(false);
        return;
      }
    }
    navigate(`/viaje/${id}`);
  };

  const alertaNivel = viaje?.alertaNivel ?? 'VERDE';
  const centro = viaje?.origen && viaje?.destino
    ? { lat: (viaje.origen.lat + viaje.destino.lat) / 2, lng: (viaje.origen.lng + viaje.destino.lng) / 2 }
    : { lat: 6.2442, lng: -75.5812 };

  return (
    <div style={{ position: 'relative', height: 'calc(100vh - 65px)', width: '100%' }}>
      <Map
        defaultCenter={centro}
        defaultZoom={13}
        mapId="mdva-map"
        colorScheme="DARK"
        gestureHandling="greedy"
        disableDefaultUI={false}
        style={{ width: '100%', height: '100%' }}
      >
        {viaje && <CapaRuta viaje={viaje} posicion={posicion} />}
      </Map>

      {/* Panel inferior */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: 'rgba(10,12,16,0.92)', backdropFilter: 'blur(12px)',
        borderTop: '1px solid #1e2330', padding: '1.25rem 1.5rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem',
      }}>
        <div>
          <div style={{ fontSize: '0.72rem', color: '#5a6070', fontFamily: 'DM Mono, monospace', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.3rem' }}>
            En ruta
          </div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
            {viaje?.origen?.displayName ?? '...'} → {viaje?.destino?.displayName ?? '...'}
          </div>
          {posicion ? (
            <div style={{ fontSize: '0.72rem', color: '#4af0a0', fontFamily: 'DM Mono, monospace', marginTop: '0.25rem' }}>
              GPS activo · {posicion.lat.toFixed(5)}, {posicion.lng.toFixed(5)}
            </div>
          ) : (
            <div style={{ fontSize: '0.72rem', color: '#5a6070', fontFamily: 'DM Mono, monospace', marginTop: '0.25rem' }}>
              Esperando GPS...
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
          <span className={`alerta-badge alerta-${alertaNivel}`}>{alertaNivel}</span>
          <button
            className="btn btn-danger"
            onClick={handleFinalizar}
            disabled={finalizando}
            style={{ whiteSpace: 'nowrap' }}
          >
            {finalizando ? 'Finalizando...' : 'Finalizar viaje'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box" style={{ position: 'absolute', top: '1rem', left: '1rem', right: '1rem' }}>
          {error}
        </div>
      )}
    </div>
  );
}