import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import PlanificarViaje from './pages/PlanificarViaje';
import ResultadoViaje from './pages/ResultadoViaje';
import HistorialViajes from './pages/HistorialViajes';
import Login from './pages/Login';
import Register from './pages/Register';
import MapaCiudad from './pages/MapaCiudad';
import EnRuta from './pages/EnRuta';
import ThemeToggle from './components/ThemeToggle';
import { APIProvider } from '@vis.gl/react-google-maps';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  // Apply persisted theme on mount
  useEffect(() => {
    const saved = localStorage.getItem('mdva-theme') ?? 'dark';
    document.documentElement.setAttribute('data-theme', saved);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = '/login';
  };

  const username = localStorage.getItem('username');

  return (
    <BrowserRouter>
      <header className="nav-header">
        <div className="nav-left">
          <span className="nav-logo">MDVA</span>
          <nav>
            <NavLink to="/" end>Mapa</NavLink>
            <NavLink to="/planificar" end>Planificar</NavLink>
            <NavLink to="/historial/1">Historial</NavLink>
          </nav>
        </div>
        <div className="nav-right">
          <ThemeToggle />
          {username && (
            <button onClick={handleLogout} className="btn-logout">
              {username} · Salir
            </button>
          )}
        </div>
      </header>

      <main style={{
        maxWidth: 'none',
        padding: 0,
        height: 'calc(100dvh - 57px)',
        width: '100%',
        overflowX: 'hidden',
        overflowY: 'auto',
      }}>
        <APIProvider apiKey={MAPS_KEY} libraries={['geometry', 'places']}>
          <Routes>
            <Route path="/login"    element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<PrivateRoute><MapaCiudad /></PrivateRoute>} />
            <Route path="/planificar" element={<PrivateRoute><PlanificarViaje /></PrivateRoute>} />
            <Route path="/viaje/:id" element={<PrivateRoute><ResultadoViaje /></PrivateRoute>} />
            <Route path="/viaje/:id/en-ruta" element={<PrivateRoute><EnRuta /></PrivateRoute>} />
            <Route path="/historial/:idUsuario" element={<PrivateRoute><HistorialViajes /></PrivateRoute>} />
          </Routes>
        </APIProvider>
      </main>
    </BrowserRouter>
  );
}
