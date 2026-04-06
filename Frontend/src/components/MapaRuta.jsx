import { APIProvider, Map, useMap } from '@vis.gl/react-google-maps';
import { useEffect } from 'react';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;

function PolylineLayer({ encodedPolyline, origen, destino }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !encodedPolyline) return;

    // Decode the overview polyline using Google Maps geometry library
    const path = window.google.maps.geometry.encoding.decodePath(encodedPolyline);

    const polyline = new window.google.maps.Polyline({
      path,
      strokeColor: '#4af0a0',
      strokeOpacity: 0.9,
      strokeWeight: 4,
      map,
    });

    // Fit bounds to the route
    const bounds = new window.google.maps.LatLngBounds();
    path.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });

    // Origin marker
    new window.google.maps.Marker({
      position: { lat: origen.lat, lng: origen.lng },
      map,
      title: origen.displayName,
      icon: {
        path: window.google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#4af0a0',
        fillOpacity: 1,
        strokeColor: '#0a0c10',
        strokeWeight: 2,
      },
    });

    // Destination marker
    new window.google.maps.Marker({
      position: { lat: destino.lat, lng: destino.lng },
      map,
      title: destino.displayName,
      icon: {
        path: window.google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#f0a04a',
        fillOpacity: 1,
        strokeColor: '#0a0c10',
        strokeWeight: 2,
      },
    });

    return () => {
      polyline.setMap(null);
    };
  }, [map, encodedPolyline, origen, destino]);

  return null;
}

export default function MapaRuta({ encodedPolyline, origen, destino }) {
  return (
    <div className="map-container">
      <APIProvider apiKey={MAPS_KEY} libraries={['geometry']}>
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
          />
        </Map>
      </APIProvider>
    </div>
  );
}
