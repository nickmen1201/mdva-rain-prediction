import { useEffect, useRef } from 'react';
import { useMap } from '../map/MapView';

const MIN_CAMERA_MOVE_METERS = 2;
const MIN_HEADING_DELTA_DEGREES = 0.7;

function toRad(value) {
  return value * Math.PI / 180;
}

function distanceMeters(a, b) {
  if (!a || !b) return Infinity;
  const earthRadius = 6371000;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const x = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat))
    * Math.sin(dLng / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function shortestAngle(from, to) {
  return ((((to - from) % 360) + 540) % 360) - 180;
}

function smoothHeading(previous, next) {
  if (previous == null) return next ?? 0;
  if (next == null) return previous;
  return (previous + shortestAngle(previous, next) * 0.72 + 360) % 360;
}

export default function useNavigationCamera({
  enabled,
  position,
  heading,
  recenterTick = 0,
  zoom = 19,
  tilt = 45,
}) {
  const map = useMap();
  const lastCameraPositionRef = useRef(null);
  const lastCameraHeadingRef = useRef(null);
  const lastRecenterTickRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (!enabled) {
      map.easeTo({ pitch: 0, bearing: 0, duration: 400 });
      return;
    }

    if (!position) return;

    const lastPosition = lastCameraPositionRef.current;
    const nextHeading = smoothHeading(lastCameraHeadingRef.current, heading ?? 0);
    const headingDelta = Math.abs(shortestAngle(lastCameraHeadingRef.current ?? nextHeading, nextHeading));
    const movedEnough = !lastPosition || distanceMeters(lastPosition, position) >= MIN_CAMERA_MOVE_METERS;
    const forceRecenter = recenterTick !== lastRecenterTickRef.current;

    if (!forceRecenter && !movedEnough && headingDelta < MIN_HEADING_DELTA_DEGREES) {
      return;
    }

    lastCameraHeadingRef.current = nextHeading;
    lastCameraPositionRef.current = position;
    lastRecenterTickRef.current = recenterTick;

    // MapLibre: pitch = inclinación, bearing = rumbo (spec 011, misma cámara de navegación 3D)
    map.easeTo({
      center: [position.lng, position.lat],
      zoom,
      pitch: tilt,
      bearing: nextHeading,
      duration: forceRecenter ? 600 : 250,
    });
  }, [enabled, heading, map, position, recenterTick, tilt, zoom]);
}
