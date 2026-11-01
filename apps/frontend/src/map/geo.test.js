import { describe, expect, it } from 'vitest';
import { boundsOf, decodePolyline, toLngLat } from './geo';

describe('decodePolyline', () => {
  it('decodifica el ejemplo oficial del formato (precisión 1e-5)', () => {
    expect(decodePolyline('_p~iF~ps|U_ulLnnqC_mqNvxq`@')).toEqual([
      { lat: 38.5, lng: -120.2 },
      { lat: 40.7, lng: -120.95 },
      { lat: 43.252, lng: -126.453 },
    ]);
  });

  it('cadena vacía o nula → sin puntos', () => {
    expect(decodePolyline('')).toEqual([]);
    expect(decodePolyline(null)).toEqual([]);
  });
});

describe('boundsOf / toLngLat', () => {
  it('caja [[oeste, sur], [este, norte]] ignorando puntos inválidos', () => {
    const pts = [{ lat: 6.25, lng: -75.57 }, { lat: 6.2, lng: -75.6 }, { lat: null, lng: 1 }];
    expect(boundsOf(pts)).toEqual([[-75.6, 6.2], [-75.57, 6.25]]);
    expect(boundsOf([])).toBeNull();
    expect(toLngLat({ lat: 6.2, lng: -75.5 })).toEqual([-75.5, 6.2]);
  });
});
