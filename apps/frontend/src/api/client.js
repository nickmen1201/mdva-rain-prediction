import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor to add JWT token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Sesión vencida o token inválido (p. ej. tras reiniciar el Backend con otro secreto):
// limpiar la sesión y volver al login en lugar de mostrar un error genérico.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url ?? '';
    if (status === 401 && !url.startsWith('/auth/')) {
      ['token', 'username', 'userId'].forEach((k) => localStorage.removeItem(k));
      if (window.location.pathname !== '/login') window.location.assign('/login?expired=1');
    }
    return Promise.reject(error);
  },
);

export const login = (data) =>
  api.post('/auth/login', data).then((r) => r.data);

export const register = (data) =>
  api.post('/auth/register', data).then((r) => r.data);

export const planificarViaje = (data) =>
  api.post('/api/viajes/planificar', data).then((r) => r.data);

export const finalizarViaje = (id, userRating) =>
  api.patch(`/api/viajes/${id}/finalizar${userRating ? `?userRating=${userRating}` : ''}`).then((r) => r.data);

export const getViajeById = (id) =>
  api.get(`/api/viajes/${id}`).then((r) => r.data);

export const getHistorial = (idUsuario) =>
  api.get(`/api/viajes/usuario/${idUsuario}`).then((r) => r.data);

// ── Sprint 5.2A: Active monitoring ──────────────────────────────────────────
export const reportarPosicion = (idViaje, latActual, lngActual) =>
  api.post(`/api/viajes/${idViaje}/posicion`, { latActual, lngActual }).then((r) => r.data);

export const obtenerAlertas = (idViaje) =>
  api.get(`/api/viajes/${idViaje}/alertas`).then((r) => r.data);

export const marcarAlertaLeida = (idViaje, idAlerta) =>
  api.patch(`/api/viajes/${idViaje}/alertas/${idAlerta}/leer`).then((r) => r.data);

// Recalcula alerta sobre el origen del viaje sin recomputar la ruta.
export const obtenerAlertaActual = (idViaje) =>
  api.get(`/api/viajes/${idViaje}/alerta-actual`).then((r) => r.data);

// ── Sprint 5.2B: Weather grid heatmap ───────────────────────────────────────
export const predictWeatherGrid = (puntos, config = {}) =>
  api.post('/api/weather/predict-grid', { puntos }, config).then((r) => r.data);

// ── Predicción horaria (punto 5 feedback) ───────────────────────────────────
export const getWeatherForecast = (latitude, longitude, hours = 6) =>
  api.get('/api/weather/forecast', { params: { latitude, longitude, hours } }).then((r) => r.data);

// ── Geocodificación con Nominatim vía Backend (spec 008/011) ────────────────
// Búsqueda al enviar el texto (no por tecla): la política de Nominatim prohíbe el autocompletado.
export const suggestPlaces = (q, signal) =>
  api.get('/api/geocoding/suggest', { params: { q }, signal }).then((r) => r.data);

export const searchPlaces = (q) =>
  api.get('/api/geocoding/search', { params: { q } }).then((r) => r.data);

export const reversePlace = (lat, lng) =>
  api.get('/api/geocoding/reverse', { params: { lat, lng } }).then((r) => r.data);
