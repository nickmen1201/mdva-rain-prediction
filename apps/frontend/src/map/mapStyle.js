// Estilo de mapa base sin API key (spec 011): teselas raster de OpenStreetMap con su atribución
// obligatoria. El tema oscuro se obtiene invirtiendo el brillo y rotando el tono en la propia capa
// raster (sin otro proveedor: las teselas oscuras de CARTO ahora exigen API key). URL configurable
// para apuntar a un servidor de teselas propio.

const TILES = import.meta.env.VITE_TILES_URL ?? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const PAINT = {
  light: {
    'raster-brightness-min': 0,
    'raster-brightness-max': 1,
    'raster-hue-rotate': 0,
    'raster-saturation': 0,
    'raster-contrast': 0,
  },
  // brightness-min > brightness-max invierte la imagen; la rotación de 180° devuelve agua azul y parques verdes
  dark: {
    'raster-brightness-min': 0.92,
    'raster-brightness-max': 0.06,
    'raster-hue-rotate': 180,
    'raster-saturation': -0.35,
    'raster-contrast': 0.1,
  },
};

export const basePaint = (theme) => PAINT[theme === 'light' ? 'light' : 'dark'];

export function baseStyle(theme) {
  return {
    version: 8,
    sources: {
      base: { type: 'raster', tiles: [TILES], tileSize: 256, maxzoom: 19, attribution: ATTRIBUTION },
    },
    layers: [{ id: 'base', type: 'raster', source: 'base', paint: basePaint(theme) }],
  };
}

export const currentTheme = () => document.documentElement.getAttribute('data-theme') ?? 'dark';
