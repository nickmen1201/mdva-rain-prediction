import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const planificarViaje = (data) =>
  api.post('/api/viajes/planificar', data).then((r) => r.data);

export const finalizarViaje = (id) =>
  api.patch(`/api/viajes/${id}/finalizar`).then((r) => r.data);

export const getViajeById = (id) =>
  api.get(`/api/viajes/${id}`).then((r) => r.data);

export const getHistorial = (idUsuario) =>
  api.get(`/api/viajes/usuario/${idUsuario}`).then((r) => r.data);
