import { useEffect } from 'react';
import { boundsOf, decodePolyline } from '../map/geo';
import MapView, { useMap } from '../map/MapView';
import { circleMarker, removeLayer, setLine } from '../map/primitives';

const ID = 'mdva-route';

function PolylineLayer({ encodedPolyline, origen, destino, paradas }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !encodedPolyline) return undefined;

    const path = decodePolyline(encodedPolyline);
    setLine(map, ID, path, { color: '#4af0a0', width: 4, opacity: 0.9 });

    const bounds = boundsOf(path);
    if (bounds) map.fitBounds(bounds, { padding: 40, duration: 0 });

    const markers = [
      circleMarker(map, origen, { color: '#4af0a0', size: 18, title: origen.displayName }),
      ...(paradas ?? []).map((p) => circleMarker(map, p, { color: '#c084fc', size: 14, title: p.displayName })),
      circleMarker(map, destino, { color: '#f0a04a', size: 18, title: destino.displayName }),
    ];

    return () => {
      markers.forEach((m) => m.remove());
      removeLayer(map, ID);
    };
  }, [map, encodedPolyline, origen, destino, paradas]);

  return null;
}

export default function MapaRuta({ encodedPolyline, origen, destino, paradas }) {
  return (
    <MapView center={{ lat: (origen.lat + destino.lat) / 2, lng: (origen.lng + destino.lng) / 2 }} zoom={12}>
      <PolylineLayer encodedPolyline={encodedPolyline} origen={origen} destino={destino} paradas={paradas} />
    </MapView>
  );
}
