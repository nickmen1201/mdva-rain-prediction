import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import PlanificarViaje from './pages/PlanificarViaje';
import ResultadoViaje from './pages/ResultadoViaje';
import HistorialViajes from './pages/HistorialViajes';

export default function App() {
  return (
    <BrowserRouter>
      <header className="nav-header">
        <span className="nav-logo">MDVA</span>
        <nav>
          <NavLink to="/" end>Planificar</NavLink>
          <NavLink to="/historial/1">Historial</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<PlanificarViaje />} />
          <Route path="/viaje/:id" element={<ResultadoViaje />} />
          <Route path="/historial/:idUsuario" element={<HistorialViajes />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
