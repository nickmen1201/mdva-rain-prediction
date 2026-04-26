import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import PlanificarViaje from './pages/PlanificarViaje';
import ResultadoViaje from './pages/ResultadoViaje';
import HistorialViajes from './pages/HistorialViajes';
import Login from './pages/Login';
import Register from './pages/Register';
import MapaCiudad from './pages/MapaCiudad';
import EnRuta from './pages/EnRuta';
import { APIProvider } from '@vis.gl/react-google-maps';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = '/login';
  };

  return (
    <BrowserRouter>
      <header className="nav-header">
        <span className="nav-logo">MDVA</span>
        <nav>
          <NavLink to="/" end>Mapa</NavLink>
          <NavLink to="/planificar" end>Planificar</NavLink>
          <NavLink to="/historial/1">Historial</NavLink>
          {localStorage.getItem('token') && (
            <button onClick={handleLogout} style={{ background: 'transparent', border: '1px solid #fff', color: '#fff', padding: '5px 10px', marginLeft: '10px', borderRadius: '4px', cursor: 'pointer' }}>
              Salir ({localStorage.getItem('username')})
            </button>
          )}
        </nav>
      </header>
      <main style={{ maxWidth: 'none', padding: 0, height: 'calc(100vh - 65px)' }}>
        <APIProvider apiKey={MAPS_KEY} libraries={['geometry', 'places']}>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={
            <PrivateRoute>
              <MapaCiudad />
            </PrivateRoute>
          } />
          <Route path="/planificar" element={
            <PrivateRoute>
              <PlanificarViaje />
            </PrivateRoute>
          } />
          <Route path="/viaje/:id" element={
            <PrivateRoute>
              <ResultadoViaje />
            </PrivateRoute>
          } />
          <Route path="/viaje/:id/en-ruta" element={
            <PrivateRoute>
              <EnRuta />
            </PrivateRoute>
          } />
          <Route path="/historial/:idUsuario" element={
            <PrivateRoute>
              <HistorialViajes />
            </PrivateRoute>
          } />
        </Routes>
        </APIProvider>
      </main>
    </BrowserRouter>
  );
}
