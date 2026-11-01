import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { basePaint, baseStyle, currentTheme } from './mapStyle';

// Mapa MapLibre con teselas OSM (spec 011). Los hijos acceden al mapa con useMap(),
// igual que con el proveedor anterior, y solo se montan cuando el estilo está cargado.
const MapContext = createContext(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useMap() {
  return useContext(MapContext);
}

export default function MapView({ center, zoom = 13, onClick, onDragStart, children, style }) {
  const containerRef = useRef(null);
  const onClickRef = useRef(onClick);
  const onDragStartRef = useRef(onDragStart);
  const [map, setMap] = useState(null);

  useEffect(() => {
    onClickRef.current = onClick;
    onDragStartRef.current = onDragStart;
  }, [onClick, onDragStart]);

  useEffect(() => {
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle(currentTheme()),
      center: [center.lng, center.lat],
      zoom,
      maxPitch: 70,
      attributionControl: { compact: true },
    });
    instance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    instance.on('click', (e) => onClickRef.current?.({ lat: e.lngLat.lat, lng: e.lngLat.lng }));
    instance.on('dragstart', () => onDragStartRef.current?.());
    instance.on('load', () => setMap(instance));

    // Tema claro/oscuro: cambia solo la pintura de la capa base, sin perder las capas agregadas encima
    const observer = new MutationObserver(() => {
      Object.entries(basePaint(currentTheme())).forEach(([prop, value]) => {
        if (instance.getLayer('base')) instance.setPaintProperty('base', prop, value);
      });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return () => {
      observer.disconnect();
      instance.remove();
      setMap(null);
    };
    // El mapa se crea una sola vez; el centro inicial no se vuelve a aplicar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div ref={containerRef} className="map-container" style={{ width: '100%', height: '100%', ...style }}>
      {map && <MapContext.Provider value={map}>{children}</MapContext.Provider>}
    </div>
  );
}
