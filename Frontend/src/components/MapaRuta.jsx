import { APIProvider, Map, useMap } from '@vis.gl/react-google-maps';
import { useEffect, useRef } from 'react';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;

function PolylineLayer({ encodedPolyline, origen, destino, paradas }) {
  const map = useMap();
  const markersRef = useRef([]);

  useEffect(() => {
    if (!map || !encodedPolyline) return;

    const path = window.google.maps.geometry.encoding.decodePath(encodedPolyline);

    const polyline = new window.google.maps.Polyline({
      path,
      strokeColor: '#4af0a0',
      strokeOpacity: 0.9,
      strokeWeight: 4,
      map,
    });

    const bounds = new window.google.maps.LatLngBounds();
    path.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });

    // Limpia marcadores anteriores
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];

    const makeMarker = (position, title, fillColor, scale) => {
      const m = new window.google.maps.Marker({
        position,
        map,
        title,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale,
          fillColor,
          fillOpacity: 1,
          strokeColor: '#0a0c10',
          strokeWeight: 2,
        },
      });
      markersRef.current.push(m);
    };

    // Origen (verde)
    makeMarker({ lat: origen.lat, lng: origen.lng }, origen.displayName, '#4af0a0', 9);

    // Paradas intermedias (violeta)
    paradas?.forEach(p => makeMarker({ lat: p.lat, lng: p.lng }, p.displayName, '#c084fc', 7));

    // Destino (naranja)
    makeMarker({ lat: destino.lat, lng: destino.lng }, destino.displayName, '#f0a04a', 9);

    return () => {
      polyline.setMap(null);
      markersRef.current.forEach(m => m.setMap(null));
      markersRef.current = [];
    };
  }, [map, encodedPolyline, origen, destino, paradas]);

  return null;
}

export default function MapaRuta({ encodedPolyline, origen, destino, paradas }) {
  return (
    <div className="map-container" style={{ height: '100%', width: '100%' }}>
      <Map
        defaultCenter={{ lat: (origen.lat + destino.lat) / 2, lng: (origen.lng + destino.lng) / 2 }}
        defaultZoom={12}
        mapId="mdva-map"
        colorScheme="DARK"
        gestureHandling="greedy"
        disableDefaultUI={false}
        style={{ width: '100%', height: '100%' }}
      >
        <PolylineLayer
          encodedPolyline={encodedPolyline}
          origen={origen}
          destino={destino}
          paradas={paradas}
        />
      </Map>
    </div>
  );
}
