import { describe, expect, it } from 'vitest';
import { gridSampler, rainColor, rainPixels, RAIN_STOPS } from './rainScale';

const malla = (f) => {
  const pts = [];
  for (let i = 0; i < 3; i += 1) for (let j = 0; j < 3; j += 1) pts.push({ lat: 6.2 + i * 0.1, lng: -75.6 + j * 0.1, weight: f(i, j) });
  return pts;
};

describe('escala fija de probabilidad (sin re-escalar, H-35)', () => {
  it('cada corte de la leyenda tiene exactamente su color', () => {
    for (const s of RAIN_STOPS) expect(rainColor(s.p)).toEqual(s.color);
  });

  it('el color depende solo de la probabilidad: 8 % no se pinta como 34 %', () => {
    expect(rainColor(0.08)).not.toEqual(rainColor(0.34));
    expect(rainColor(0.08)).toEqual(rainColor(0.08));
    expect(rainColor(-1)).toEqual(RAIN_STOPS[0].color);
    expect(rainColor(2)).toEqual(RAIN_STOPS.at(-1).color);
  });
});

describe('muestreo bilineal de la malla', () => {
  it('reproduce los puntos y es lineal entre ellos; fuera de la malla no extrapola', () => {
    const s = gridSampler(malla((i, j) => 0.1 * i + 0.05 * j));
    expect(s(6.2, -75.6)).toBeCloseTo(0);
    expect(s(6.35, -75.45)).toBeCloseTo(0.15 + 0.075);
    expect(s(7, -75.5)).toBeNull();
  });

  it('el raster no inventa valores: probabilidad uniforme → un solo color', () => {
    const px = rainPixels(malla(() => 0.4), 8);
    const colores = new Set();
    for (let k = 0; k < px.length; k += 4) colores.add(`${px[k]},${px[k + 1]},${px[k + 2]}`);
    expect([...colores]).toEqual([RAIN_STOPS[2].color.join(',')]);
  });
});
