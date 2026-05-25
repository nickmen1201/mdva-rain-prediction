import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Map, useMap } from '@vis.gl/react-google-maps';
import { getViajeById, finalizarViaje, reportarPosicion, planificarViaje } from '../api/client';
import NavigationHeader from '../components/NavigationHeader';
import NavigationPanel from '../components/NavigationPanel';
import RecomendacionBanner from '../components/RecomendacionBanner';
import CenterButton from '../components/CenterButton';
import WeatherHeatmapLayer from '../components/WeatherHeatmapLayer';
import WeatherHeatmapToggle from '../components/WeatherHeatmapToggle';
import useNavigationCamera from '../hooks/useNavigationCamera';
import useDeviceOrientationHeading from '../hooks/useDeviceOrientationHeading';
import useWeatherGrid from '../hooks/useWeatherGrid';
import {
  calcularPasoActivo,
  calcularDistanciaRestante,
  haversine,
} from '../utils/navUtils';

// ── SVG arrow marker path ─────────────────────────────────────────────────────
const NAV_ARROW_PATH = 'M 0,-14 L 6,8 L 0,4 L -6,8 Z';
const RAIN_HEATMAP_STORAGE_KEY = 'mdva-rain-heatmap-enabled';

function getClimateStatus(alertaNivel, alertaActiva, prediccion) {
  const nivel = alertaActiva?.nivelSeveridad ?? alertaNivel ?? 'VERDE';
  const prob = prediccion?.probabilidadRf;

  if (nivel === 'CRISIS') return { label: 'RIESGO CRÍTICO', cls: 'danger' };
  if (nivel === 'PELIGRO' || nivel === 'ROJO') return { label: 'LLUVIA FUERTE', cls: 'danger' };
  if (nivel === 'PRECAUCION' || nivel === 'AMARILLO') return { label: 'PRECAUCIÓN', cls: 'warn' };
  if (prob != null && prob >= 0.55) return { label: 'LLUVIA POSIBLE', cls: 'warn' };
  if (prob != null && prob < 0.25) return { label: 'CLIMA FAVORABLE', cls: 'clear' };
  return { label: 'ESTABLE', cls: 'clear' };
}

function bearingBetween(a, b) {
  const startLat = a.lat * Math.PI / 180;
  const endLat = b.lat * Math.PI / 180;
  const deltaLng = (b.lng - a.lng) * Math.PI / 180;
  const y = Math.sin(deltaLng) * Math.cos(endLat);
  const x = Math.cos(startLat) * Math.sin(endLat)
    - Math.sin(startLat) * Math.cos(endLat) * Math.cos(deltaLng);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

// ── Subcomponent: draws route, animated GPS marker ────────────────────────────
function obtenerPosicionActual() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('NO_GEOLOCATION'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lng: coords.longitude }),
      reject,
      { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 },
    );
  });
}

function CapaRuta({ viaje, posicion, heading, pasoActivo, theme, paradas }) {
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
    paradas?.forEach((p, i) => {
      const m = new window.google.maps.Marker({
        position: { lat: p.lat, lng: p.lng },
        map,
        title: p.displayName ?? `Parada ${i + 1}`,
        zIndex: 6,
        label: { text: String(i + 1), color: '#0a0c10', fontWeight: 'bold', fontSize: '11px' },
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 11,
          fillColor: '#c084fc',
          fillOpacity: 1,
          strokeColor: '#0a0c10',
          strokeWeight: 2,
        },
      });
      markers.push(m);
    });
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

  }, [map, posicion, heading]);

  return null;
}

function NavigationCamera({ enabled, position, heading, recenterTick }) {
  useNavigationCamera({ enabled, position, heading, recenterTick, zoom: 19, tilt: 60 });
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
  const [transitioning, setTransitioning] = useState(false);
  const [arrivalPromptOpen, setArrivalPromptOpen] = useState(false);
  const [finishPromptOpen, setFinishPromptOpen] = useState(false);
  const [recenterTick, setRecenterTick] = useState(0);
  const [heatmapEnabled, setHeatmapEnabled] = useState(
    () => localStorage.getItem(RAIN_HEATMAP_STORAGE_KEY) !== 'false',
  );
  const [gyroRotationEnabled, setGyroRotationEnabled] = useState(
    () => localStorage.getItem('mdva-gyro-rotation-enabled') !== 'false',
  );
  const {
    heading: deviceHeading,
    supported: orientationSupported,
    permissionState: orientationPermission,
    requestAccess: requestOrientationAccess,
  } = useDeviceOrientationHeading();
  
  // Pending stops for trip chaining
  const [pendingStops]  = useState(state?.pendingStops ?? []);

  // Paradas intermedias para marcadores en mapa (estables, no cambian)
  const [paradas] = useState(state?.paradas ?? []);
  const itinerary = state?.itinerary ?? null;
  const parentViajeId = state?.parentViajeId ?? null;

  const watchId      = useRef(null);
  const lastHeading  = useRef(0);
  const lastGpsPoint = useRef(null);
  const posicionRef  = useRef(null);
  const pollingTimer = useRef(null);
  const transitionRef = useRef(false);
  const cameraHeading = gyroRotationEnabled ? (deviceHeading ?? heading) : heading;

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
      const timer = window.setTimeout(() => {
        setEta(Date.now() + viaje.tiempoEstimadoMin * 60_000);
      }, 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [viaje]);

  // GPS watch
  useEffect(() => {
    if (!navigator.geolocation) {
      const timer = window.setTimeout(() => setError('Este navegador no soporta GPS.'), 0);
      return () => window.clearTimeout(timer);
    }

    watchId.current = navigator.geolocation.watchPosition(
      ({ coords }) => {
        const pos = { lat: coords.latitude, lng: coords.longitude };
        const previous = lastGpsPoint.current;
        setPosicion(pos);
        posicionRef.current = pos;
        lastGpsPoint.current = pos;

        const movedEnough = previous
          ? haversine(previous.lat, previous.lng, pos.lat, pos.lng) > 5
          : false;
        const targetHeading = coords.heading != null && !isNaN(coords.heading)
          ? coords.heading
          : movedEnough
            ? bearingBetween(previous, pos)
            : null;

        if (targetHeading != null) {
          // Low-pass filter para amortiguar el tembleque del heading bajo ruido GPS.
          // diff usa el camino angular más corto para evitar saltos al cruzar 0/360.
          const diff = ((targetHeading - lastHeading.current + 540) % 360) - 180;
          const smoothed = (lastHeading.current + diff * 0.25 + 360) % 360;
          lastHeading.current = smoothed;
          setHeading(smoothed);
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
  const handleAutoNextLeg = useCallback(async () => {
    if (!viaje || pendingStops.length === 0) return;
    setError(null);

    let originPoint = null;
    try {
      originPoint = await obtenerPosicionActual();
      setPosicion(originPoint);
      posicionRef.current = originPoint;
      lastGpsPoint.current = originPoint;
    } catch (err) {
      console.warn('No se pudo obtener GPS fresco para el siguiente tramo.', err);
      originPoint = posicionRef.current ?? posicion;
    }

    if (!originPoint?.lat || !originPoint?.lng) {
      setError('No se pudo iniciar el siguiente tramo porque no pudimos obtener tu ubicacion actual.');
      transitionRef.current = false;
      setTransitioning(false);
      return;
    }

    try {
      // 1. Finish current leg
      try {
        await finalizarViaje(id);
      } catch (err) {
        if (err.response?.status !== 409) throw err;
      }
      
      // 2. Prepare next leg
      const nextDest = pendingStops[0];
      const remaining = pendingStops.slice(1);
      
      const idVehiculoViaje = viaje.idVehiculo ?? state?.idVehiculo ?? null;
      const tipoVehiculoViaje = viaje.tipoVehiculo ?? state?.tipoVehiculo ?? 'CARRO';
      const payload = {
        idVehiculo: idVehiculoViaje,
        tipoVehiculo: tipoVehiculoViaje,
        origen: {
          lat: originPoint.lat,
          lng: originPoint.lng,
          displayName: "Mi ubicación actual",
        },
        destino: nextDest,
        paradas: [],
        modoParadas: 'ORDEN_INGRESADO',
      };

      // 3. Create next trip
      const nextViaje = await planificarViaje(payload);
      
      // 4. Reload page for next leg
      navigate(`/viaje/${nextViaje.idViaje}/en-ruta`, {
        replace: true,
        state: {
          viaje: nextViaje,
          pendingStops: remaining,
          paradas,
          itinerary,
          parentViajeId,
          idVehiculo: idVehiculoViaje,
          tipoVehiculo: tipoVehiculoViaje,
        }
      });
      
      // Reset flags after small delay
      setTimeout(() => {
        transitionRef.current = false;
        setTransitioning(false);
      }, 2000);
      
    } catch (err) {
      console.error("Chaining failed:", err);
      transitionRef.current = false;
      setTransitioning(false);
      const msg = err.response?.data?.detail
        ?? err.response?.data?.message
        ?? err.message
        ?? 'No se pudo iniciar el siguiente tramo.';
      setError(msg);
    }
  }, [id, itinerary, navigate, paradas, parentViajeId, pendingStops, posicion, state, viaje]);

  // Auto-Chaining Logic: Detect stop arrival
  useEffect(() => {
    if (!posicion || !viaje || transitionRef.current || finalizando) return;

    const distToDest = haversine(posicion.lat, posicion.lng, viaje.destino.lat, viaje.destino.lng);

    if (distToDest < 50 && pendingStops.length > 0) {
      transitionRef.current = true;
      window.setTimeout(() => setArrivalPromptOpen(true), 0);
    }
  }, [posicion, viaje, pendingStops, finalizando, handleAutoNextLeg]);

  const handleContinuarCola = () => {
    setArrivalPromptOpen(false);
    setFinishPromptOpen(false);
    setTransitioning(true);
    handleAutoNextLeg();
  };

  // Step & ETA update
  useEffect(() => {
    if (!posicion || !viaje?.pasos?.length) return;
    const timer = window.setTimeout(() => {
      const idx = calcularPasoActivo(viaje.pasos, posicion);
      setPasoActivo(idx);
      const rem = calcularDistanciaRestante(viaje.pasos, idx, posicion);
      setDistRestante(rem);
      if (viaje?.distanciaMetros && viaje?.tiempoEstimadoMin && rem != null) {
        const speed = viaje.distanciaMetros / (viaje.tiempoEstimadoMin * 60);
        if (speed > 0) setEta(Date.now() + (rem / speed) * 1000);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [posicion, viaje]);

  // Polling
  const doPolling = useCallback(async () => {
    const pos = posicionRef.current;
    if (!pos) return;
    try {
      const res = await reportarPosicion(id, pos.lat, pos.lng);
      if (res?.alertaNueva) setAlertaActiva(res.alertaNueva);
    } catch (err) {
      console.warn('No se pudo reportar la posicion actual.', err);
    }
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
    setArrivalPromptOpen(false);
    setFinishPromptOpen(true);
  };

  const handleConfirmarFinalizarTodo = async () => {
    setFinalizando(true);
    let finalizado = null;
    try {
      finalizado = await finalizarViaje(id);
    } catch (err) {
      if (err.response?.status !== 409) {
        setError('Error al finalizar el viaje.');
        setFinalizando(false);
        return;
      }
    }
    const finishedAt = finalizado?.horaFin ?? new Date().toISOString();
    navigate('/', {
      replace: true,
      state: {
        tripSummary: {
          ...viaje,
          ...finalizado,
          idViaje: viaje?.idViaje ?? finalizado?.idViaje ?? Number(id),
          origen: viaje?.origen,
          destino: viaje?.destino,
          prediccionLluvia: viaje?.prediccionLluvia,
          alertaNivel: viaje?.alertaNivel,
          distanciaMetros: viaje?.distanciaMetros ?? finalizado?.distanciaMetros,
          tiempoEstimadoMin: viaje?.tiempoEstimadoMin ?? finalizado?.tiempoEstimadoMin,
          horaInicio: viaje?.horaInicio ?? finalizado?.horaInicio,
          horaFin: finishedAt,
          pendingStopsCount: pendingStops.length,
          completedStops: itinerary?.length ? itinerary : [viaje?.origen, ...paradas, viaje?.destino].filter(Boolean),
        },
      }
    });
  };

  const alertaNivel   = viaje?.alertaNivel ?? 'VERDE';
  const climateStatus = getClimateStatus(alertaNivel, alertaActiva, viaje?.prediccionLluvia);
  const centro        = viaje?.origen && viaje?.destino
    ? { lat: (viaje.origen.lat + viaje.destino.lat) / 2, lng: (viaje.origen.lng + viaje.destino.lng) / 2 }
    : { lat: 6.2442, lng: -75.5812 };
  const pasoActualData = viaje?.pasos?.[pasoActivo] ?? null;
  const heatmapCenter = posicion ?? centro;
  const { points: heatmapPoints, loading: heatmapLoading, error: heatmapError } = useWeatherGrid({
    enabled: heatmapEnabled,
    center: heatmapCenter,
    gridSize: 9,
    spacingKm: 0.48,
    minMoveMeters: posicion ? 700 : 0,
  });

  const toggleHeatmap = () => {
    setHeatmapEnabled((current) => {
      const next = !current;
      localStorage.setItem(RAIN_HEATMAP_STORAGE_KEY, String(next));
      return next;
    });
  };

  const toggleGyroRotation = async () => {
    if (!gyroRotationEnabled && orientationSupported && orientationPermission !== 'granted') {
      const granted = await requestOrientationAccess();
      if (!granted) return;
    }

    setGyroRotationEnabled((current) => {
      const next = !current;
      localStorage.setItem('mdva-gyro-rotation-enabled', String(next));
      return next;
    });
  };

  const handleCenterMap = () => {
    setCentering(true);
    setRecenterTick((value) => value + 1);
  };

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <Map
        defaultCenter={centro}
        defaultZoom={16}
        mapId="mdva-nav-map"
        colorScheme={theme.toUpperCase()}
        gestureHandling="greedy"
        renderingType="VECTOR"
        disableDefaultUI
        style={{ width: '100%', height: '100%' }}
        onDragStart={() => setCentering(false)}
      >
        <NavigationCamera
          enabled={centering}
          position={posicion}
          heading={cameraHeading}
          recenterTick={recenterTick}
        />
        <WeatherHeatmapLayer
          points={heatmapPoints}
          visible={heatmapEnabled && !heatmapError}
          opacity={0.38}
        />
        {viaje && (
          <CapaRuta
            viaje={viaje}
            posicion={posicion}
            heading={cameraHeading}
            pasoActivo={pasoActivo}
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

      <div className={`nav-map-controls${panelOpen ? ' panel-open' : ''}`}>
        <CenterButton active={centering} onClick={handleCenterMap} />
        {orientationSupported && (
          <button
            onClick={toggleGyroRotation}
            className={`map-control-button${gyroRotationEnabled ? ' active' : ''}`}
            title={gyroRotationEnabled ? 'Usar rumbo por movimiento' : 'Usar giro del dispositivo'}
            aria-label={gyroRotationEnabled ? 'Desactivar giro del dispositivo' : 'Activar giro del dispositivo'}
            aria-pressed={gyroRotationEnabled}
            type="button"
          >
            Giro
          </button>
        )}
        <WeatherHeatmapToggle
          enabled={heatmapEnabled}
          loading={heatmapLoading}
          onToggle={toggleHeatmap}
        />
        <button
          onClick={() => setPanelOpen(v => !v)}
          className="map-control-button"
          aria-label="Ver lista de pasos del viaje"
          aria-expanded={panelOpen}
          title="Ver pasos"
          type="button"
        >
          Menu
        </button>
      </div>

      {heatmapEnabled && heatmapError && (
        <div className="map-toast map-toast-warning">
          {heatmapError}
        </div>
      )}

      {arrivalPromptOpen && pendingStops.length > 0 && (
        <div className="arrival-modal-overlay">
          <div className="arrival-modal-card">
            <div className="section-heading">Parada alcanzada</div>
            <h2>¿Continuar con la cola?</h2>
            <p>
              Llegaste a {viaje?.destino?.displayName ?? 'la parada actual'}.
              El siguiente destino es {pendingStops[0]?.displayName ?? 'la siguiente parada'}.
            </p>
            <div className="arrival-actions">
              <button className="btn btn-primary" onClick={handleContinuarCola} disabled={transitioning}>
                Ir a {pendingStops[0]?.displayName ?? 'siguiente parada'}
              </button>
              <button className="btn btn-danger" onClick={handleFinalizar} disabled={finalizando}>
                Finalizar viaje
              </button>
            </div>
          </div>
        </div>
      )}

      {finishPromptOpen && (
        <div className="arrival-modal-overlay">
          <div className="arrival-modal-card">
            <div className="section-heading">
              {pendingStops.length > 0 ? 'Viaje con paradas pendientes' : 'Finalizar viaje'}
            </div>
            <h2>¿Detener o continuar?</h2>
            {pendingStops.length === 0 && (
              <p>
                Vas a cerrar este trayecto y volver al mapa principal. Te mostraremos un resumen del viaje finalizado.
              </p>
            )}
            <p style={{ display: pendingStops.length > 0 ? 'block' : 'none' }}>
              Aún tienes {pendingStops.length} destino{pendingStops.length === 1 ? '' : 's'} en cola.
              El siguiente es {pendingStops[0]?.displayName ?? 'la siguiente parada'}.
            </p>
            <div className="queue-preview" style={{ display: pendingStops.length > 0 ? 'grid' : 'none' }}>
              {[viaje?.destino, ...pendingStops].filter(Boolean).map((stop, index) => (
                <div key={`${stop.lat}-${stop.lng}-${index}`} className={index === 0 ? 'done' : ''}>
                  <span>{index === 0 ? 'Actual' : `Siguiente ${index}`}</span>
                  <strong>{stop.displayName ?? 'Destino sin nombre'}</strong>
                </div>
              ))}
            </div>
            <div className="arrival-actions">
              <button className="btn btn-primary" onClick={handleContinuarCola} disabled={transitioning} style={{ display: pendingStops.length > 0 ? 'inline-flex' : 'none' }}>
                Iniciar siguiente en cola
              </button>
              <button className="btn btn-danger" onClick={handleConfirmarFinalizarTodo} disabled={finalizando}>
                {finalizando ? <><span className="spinner" /> Finalizando...</> : 'Confirmar finalización'}
              </button>
              <button className="btn btn-secondary" onClick={() => setFinishPromptOpen(false)}>
                Volver al mapa
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chaining notification */}
      {transitioning && (
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
            <span className={`climate-chip ${climateStatus.cls}`}>{climateStatus.label}</span>
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
