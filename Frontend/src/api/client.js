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
