import { useCallback, useEffect, useRef, useState } from 'react';

const hasDeviceOrientation =
  typeof window !== 'undefined' && 'DeviceOrientationEvent' in window;

const needsExplicitPermission =
  hasDeviceOrientation
  && typeof window.DeviceOrientationEvent.requestPermission === 'function';

const HEADING_ALPHA = 0.18;
const HEADING_DEADBAND_DEGREES = 0.75;
const SPIKE_LIMIT_DEGREES = 55;

function shortestAngle(from, to) {
  return ((((to - from) % 360) + 540) % 360) - 180;
}

function normalizeHeading(event) {
  if (typeof event.webkitCompassHeading === 'number') {
    return event.webkitCompassHeading;
  }

  if (typeof event.alpha === 'number') {
    return (360 - event.alpha + 360) % 360;
  }

  return null;
}

export default function useDeviceOrientationHeading() {
  const [heading, setHeading] = useState(null);
  const [supported, setSupported] = useState(hasDeviceOrientation);
  const [permissionState, setPermissionState] = useState(
    hasDeviceOrientation ? (needsExplicitPermission ? 'idle' : 'granted') : 'unsupported',
  );
  const frameRef = useRef(null);
  const latestHeadingRef = useRef(null);
  const smoothedHeadingRef = useRef(null);

  const handleOrientation = useCallback((event) => {
    const rawHeading = normalizeHeading(event);
    if (rawHeading == null) return;

    const previous = smoothedHeadingRef.current;
    let nextHeading = rawHeading;

    if (previous != null) {
      const delta = shortestAngle(previous, rawHeading);
      if (Math.abs(delta) < HEADING_DEADBAND_DEGREES) return;

      const alpha = Math.abs(delta) > SPIKE_LIMIT_DEGREES ? HEADING_ALPHA * 0.45 : HEADING_ALPHA;
      nextHeading = (previous + delta * alpha + 360) % 360;
    }

    smoothedHeadingRef.current = nextHeading;
    latestHeadingRef.current = nextHeading;
    if (frameRef.current) return;

    frameRef.current = window.requestAnimationFrame(() => {
      frameRef.current = null;
      setHeading(latestHeadingRef.current);
    });
  }, []);

  const attachListeners = useCallback(() => {
    window.addEventListener('deviceorientationabsolute', handleOrientation, true);
    window.addEventListener('deviceorientation', handleOrientation, true);
  }, [handleOrientation]);

  const requestAccess = useCallback(async () => {
    if (!('DeviceOrientationEvent' in window)) {
      setSupported(false);
      setPermissionState('unsupported');
      return false;
    }

    setSupported(true);

    try {
      if (typeof window.DeviceOrientationEvent.requestPermission === 'function') {
        const result = await window.DeviceOrientationEvent.requestPermission();
        if (result !== 'granted') {
          setPermissionState('denied');
          return false;
        }
      }

      attachListeners();
      setPermissionState('granted');
      return true;
    } catch {
      setPermissionState('denied');
      return false;
    }
  }, [attachListeners]);

  useEffect(() => {
    if (!('DeviceOrientationEvent' in window)) {
      return undefined;
    }

    if (typeof window.DeviceOrientationEvent.requestPermission !== 'function') {
      attachListeners();
    }

    return () => {
      window.removeEventListener('deviceorientationabsolute', handleOrientation, true);
      window.removeEventListener('deviceorientation', handleOrientation, true);
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
    };
  }, [attachListeners, handleOrientation]);

  return { heading, supported, permissionState, requestAccess };
}
