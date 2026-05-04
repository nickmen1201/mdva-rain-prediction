import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Map, useMap } from '@vis.gl/react-google-maps';
import { getViajeById, finalizarViaje, reportarPosicion, planificarViaje } from '../api/client';
import NavigationHeader from '../components/NavigationHeader';
import NavigationPanel from '../components/NavigationPanel';
import RecomendacionBanner from '../components/RecomendacionBanner';
import {
  calcularPasoActivo,
  calcularDistanciaRestante,
  haversine,
} from '../utils/navUtils';

// ── SVG arrow marker path ─────────────────────────────────────────────────────
const NAV_ARROW_PATH = 'M 0,-14 L 6,8 L 0,4 L -6,8 Z';

// ── Subcomponent: draws route, animated GPS marker ────────────────────────────
function CapaRuta({ viaje, posicion, heading, pasoActivo, centering, theme, paradas }) {
  const map = useMap();
  const marcadorRef  = useRef(null);
  const polylineRef  = useRef(null);
  const recorridoRef = useRef(null);

  const isDark = theme === 'dark';

  // POI markers: origen, paradas intermedias, destino
  useEffect(() => {
    if (!map || !viaje?.origen || !viaje?.destino) return;

    const markers = [];
    const makeMarker = (position, title, fillColor, scale) => {
      const m = new window.google.maps.Marker({
        position,
        map,
        title,
        zIndex: 5,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale,
          fillColor,
          fillOpacity: 1,
          strokeColor: '#0a0c10',
          strokeWeight: 2,
        },
      });
      markers.push(m);
    };

    makeMarker({ lat: viaje.origen.lat,  lng: viaje.origen.lng  }, viaje.origen.displayName  ?? 'Origen',  '#4af0a0', 8);
    paradas?.forEach(p => makeMarker({ lat: p.lat, lng: p.lng }, p.displayName ?? 'Parada', '#c084fc', 6));
    makeMarker({ lat: viaje.destino.lat, lng: viaje.destino.lng }, viaje.destino.displayName ?? 'Destino', '#f0a04a', 8);

    return () => markers.forEach(m => m.setMap(null));
  }, [map, viaje, paradas]);

  // Draw route polyline on mount
  useEffect(() => {
    if (!map || !viaje?.overviewPolyline) return;

    const path = window.google.maps.geometry.encoding.decodePath(viaje.overviewPolyline);

    // Visual Improvements: Thicker and more opaque lines
    polylineRef.current = new window.google.maps.Polyline({
      path,
      strokeColor: isDark ? '#4af0a0' : '#0a8f5c',
      strokeOpacity: 0.9,
      strokeWeight: 9,
      map,
    });

    recorridoRef.current = new window.google.maps.Polyline({
      path: [],
      strokeColor: isDark ? '#5a6070' : '#444444',
      strokeOpacity: 1.0,
      strokeWeight: 9,
      map,
    });

    // Fit map to route initially
    const bounds = new window.google.maps.LatLngBounds();
    path.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, { top: 80, right: 300, bottom: 160, left: 40 });

    return () => {
      polylineRef.current?.setMap(null);
      recorridoRef.current?.setMap(null);
    };
  }, [map, viaje, isDark]);

  // Update gray "traveled" section
  useEffect(() => {
    if (!recorridoRef.current || !viaje?.pasos || !posicion) return;
    const traveled = [];
    viaje.pasos.slice(0, pasoActivo + 1).forEach((p) => {
      if (p.startLat != null) traveled.push({ lat: p.startLat, lng: p.startLng });
    });
    traveled.push(posicion);
    recorridoRef.current.setPath(traveled);
  }, [viaje, pasoActivo, posicion]);

  // GPS marker & Navigation Mode (Closeup/Tilt/Rotate)
  useEffect(() => {
    if (!map || !posicion) return;

    const icon = {
      path: NAV_ARROW_PATH,
      fillColor: '#4af0a0',
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 3,
      scale: 1.6,
      rotation: heading ?? 0,
      anchor: new window.google.maps.Point(0, 0),
    };

    if (marcadorRef.current) {
      marcadorRef.current.setPosition(posicion);
      marcadorRef.current.setIcon(icon);
    } else {
      marcadorRef.current = new window.google.maps.Marker({
        position: posicion,
        map,
        icon,
        title: 'Tu posición',
        zIndex: 10,
      });
    }

    // Navigation Mode: "Waze/Google Maps" style closeup
    if (centering) {
      map.setCenter(posicion);
      map.setZoom(19);
      map.setTilt(45);
      map.setHeading(heading ?? 0);
    } else {
        // Reset tilt if centering is disabled? Optional, let's keep it 0 for manual browsing
        map.setTilt(0);
        map.setHeading(0);
    }
  }, [map, posicion, heading, centering]);

  return null;
}

// ── Main EnRuta page ──────────────────────────────────────────────────────────
export default function EnRuta() {
  const { id }    = useParams();
  const { state } = useLocation();
  const navigate  = useNavigate();

  const [viaje,         setViaje]         = useState(state?.viaje ?? null);
  const [posicion,      setPosicion]      = useState(null);
  const [heading,       setHeading]       = useState(0);
  const [error,         setError]         = useState(null);
  const [finalizando,   setFinalizando]   = useState(false);
  const [panelOpen,     setPanelOpen]     = useState(false);
  const [pasoActivo,    setPasoActivo]    = useState(0);
  const [distRestante,  setDistRestante]  = useState(null);
  const [eta,           setEta]           = useState(null);
  const [alertaActiva,  setAlertaActiva]  = useState(null);
  const [centering,     setCentering]     = useState(true);
  const [theme,         setTheme]         = useState('dark');
  
  // Pending stops for trip chaining
  const [pendingStops,  setPendingStops]  = useState(state?.pendingStops ?? []);

  // Paradas intermedias para marcadores en mapa (estables, no cambian)
  const [paradas] = useState(state?.paradas ?? []);

  const watchId      = useRef(null);
  const lastHeading  = useRef(0);
  const posicionRef  = useRef(null);
  const pollingTimer = useRef(null);
  const transitionRef = useRef(false);

  // Sync theme
  useEffect(() => {
    const checkTheme = () => {
      const t = document.documentElement.getAttribute('data-theme') || 'dark';
      setTheme(t);
    };
    checkTheme();
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  // Load viaje if not in state
  useEffect(() => {
    if (!viaje) {
      getViajeById(id)
        .then(setViaje)
        .catch(() => setError('No se pudo cargar el viaje.'));
    }
  }, [id, viaje]);

  // Initial ETA
  useEffect(() => {
    if (viaje?.tiempoEstimadoMin) {
      setEta(Date.now() + viaje.tiempoEstimadoMin * 60_000);
    }
  }, [viaje]);

  // GPS watch
  useEffect(() => {
    if (!navigator.geolocation) { setError('Este navegador no soporta GPS.'); return; }

    watchId.current = navigator.geolocation.watchPosition(
      ({ coords }) => {
        const pos = { lat: coords.latitude, lng: coords.longitude };
        setPosicion(pos);
        posicionRef.current = pos;

        if (coords.heading != null && !isNaN(coords.heading)) {
          lastHeading.current = coords.heading;
          setHeading(coords.heading);
        } else {
          setHeading(lastHeading.current);
        }
        setError(null);
      },
      (err) => {
        console.error("GPS Error:", err);
        setError('Error al obtener ubicación. Verifica permisos.');
      },
      { enableHighAccuracy: true, maximumAge: 1000, timeout: 15000 },
    );

    return () => navigator.geolocation.clearWatch(watchId.current);
  }, []);

  // ── Auto-Chaining Logic: Detect stop arrival ─────────────────────────────
  useEffect(() => {
    if (!posicion || !viaje || transitionRef.current || finalizando) return;

    // Check distance to current leg's destination
    const distToDest = haversine(posicion.lat, posicion.lng, viaje.destino.lat, viaje.destino.lng);
    
    // If within 50m of current stop and we have pending stops
    if (distToDest < 50 && pendingStops.length > 0) {
      transitionRef.current = true;
      handleAutoNextLeg();
    }
  }, [posicion, viaje, pendingStops, finalizando]);

  const handleAutoNextLeg = async () => {
    try {
      // 1. Finish current leg
      await finalizarViaje(id);
      
      // 2. Prepare next leg
      const nextDest = pendingStops[0];
      const remaining = pendingStops.slice(1);
      
      const payload = {
        idVehiculo: viaje.idVehiculo,
        origen: { lat: posicion.lat, lng: posicion.lng, displayName: "Mi ubicación actual" },
        destino: nextDest,
        paradas: []
      };

      // 3. Create next trip
      const nextViaje = await planificarViaje(payload);
      
      // 4. Reload page for next leg
      navigate(`/viaje/${nextViaje.idViaje}/en-ruta`, {
        replace: true,
        state: {
          viaje: nextViaje,
          pendingStops: remaining
        }
      });
      
      // Reset flags after small delay
      setTimeout(() => { transitionRef.current = false; }, 2000);
      
    } catch (err) {
      console.error("Chaining failed:", err);
      transitionRef.current = false;
    }
  };

  // Step & ETA update
  useEffect(() => {
    if (!posicion || !viaje?.pasos?.length) return;
    const idx = calcularPasoActivo(viaje.pasos, posicion);
    setPasoActivo(idx);
    const rem = calcularDistanciaRestante(viaje.pasos, idx, posicion);
    setDistRestante(rem);
    if (viaje?.distanciaMetros && viaje?.tiempoEstimadoMin && rem != null) {
      const speed = viaje.distanciaMetros / (viaje.tiempoEstimadoMin * 60);
      if (speed > 0) setEta(Date.now() + (rem / speed) * 1000);
    }
  }, [posicion, viaje]);

  // Polling
  const doPolling = useCallback(async () => {
    const pos = posicionRef.current;
    if (!pos) return;
    try {
      const res = await reportarPosicion(id, pos.lat, pos.lng);
      if (res?.alertaNueva) setAlertaActiva(res.alertaNueva);
    } catch {}
  }, [id]);

  useEffect(() => {
    if (!viaje) return;
    const nivel = alertaActiva?.nivelSeveridad;
    if (nivel === 'CRISIS') return;
    const interval = nivel === 'PELIGRO' || nivel === 'PRECAUCION' ? 30_000 : 60_000;
    pollingTimer.current = setInterval(doPolling, interval);
    return () => clearInterval(pollingTimer.current);
  }, [viaje, alertaActiva, doPolling]);

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

  const alertaNivel   = viaje?.alertaNivel ?? 'VERDE';
  const centro        = viaje?.origen && viaje?.destino
    ? { lat: (viaje.origen.lat + viaje.destino.lat) / 2, lng: (viaje.origen.lng + viaje.destino.lng) / 2 }
    : { lat: 6.2442, lng: -75.5812 };
  const pasoActualData = viaje?.pasos?.[pasoActivo] ?? null;

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <Map
        defaultCenter={centro}
        defaultZoom={16}
        mapId="mdva-nav-map"
        colorScheme={theme.toUpperCase()}
        gestureHandling="greedy"
        disableDefaultUI
        style={{ width: '100%', height: '100%' }}
        onDragStart={() => setCentering(false)}
      >
        {viaje && (
          <CapaRuta
            viaje={viaje}
            posicion={posicion}
            heading={heading}
            pasoActivo={pasoActivo}
            centering={centering}
            theme={theme}
            paradas={paradas}
          />
        )}
      </Map>

      <NavigationHeader
        paso={pasoActualData}
        distanciaRestante={distRestante}
        eta={eta}
      />

      <RecomendacionBanner
        alerta={alertaActiva}
        onCerrar={() => setAlertaActiva(null)}
      />

      <NavigationPanel
        pasos={viaje?.pasos ?? []}
        pasoActivo={pasoActivo}
        visible={panelOpen}
        onClose={() => setPanelOpen(false)}
      />

      {/* Control Buttons */}
      <div style={{
        position: 'absolute',
        top: '5.5rem',
        right: panelOpen ? '292px' : '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        transition: 'right 0.3s',
        zIndex: 11,
      }}>
        <button
          onClick={() => setCentering(true)}
          className={`btn-icon nav-hud ${centering ? 'nav-hud-accent' : ''}`}
          title="Modo Navegación"
          style={{ fontSize: '1.1rem' }}
        >
          ◉
        </button>
        <button
          onClick={() => setPanelOpen(v => !v)}
          className="btn-icon nav-hud"
          title="Ver pasos"
        >
          ☰
        </button>
      </div>

      {/* Chaining notification */}
      {transitionRef.current && (
        <div className="alerta-badge alerta-VERDE" style={{ position: 'absolute', top: '5.5rem', left: '50%', transform: 'translateX(-50%)', zIndex: 30 }}>
          Reanudando siguiente tramo...
        </div>
      )}

      {/* Bottom HUD */}
      <div className="nav-hud" style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        padding: '1rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        zIndex: 10,
      }}>
        <div>
          <div className="nav-hud-muted" style={{ fontSize: '0.75rem', fontFamily: 'DM Mono', letterSpacing: '0.1em' }}>
            {pendingStops.length > 0 ? `TRAMO ACTUAL (${pendingStops.length} pendientes)` : 'TRAMO FINAL'}
          </div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
            {viaje?.destino?.displayName ?? '...'}
          </div>
          <div style={{ marginTop: '0.25rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span className="nav-hud-accent" style={{ fontSize: '0.75rem' }}>● GPS ACTIVO</span>
            <span className={`alerta-badge alerta-${alertaNivel}`}>{alertaNivel}</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-danger" onClick={handleFinalizar} disabled={finalizando}>
            ■ Finalizar
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box" style={{ position: 'absolute', top: '5.5rem', left: '1rem', right: '1rem', zIndex: 20 }}>
          {error}
        </div>
      )}
    </div>
  );
}