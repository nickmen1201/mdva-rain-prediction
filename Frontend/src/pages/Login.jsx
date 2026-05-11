import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { login } from '../api/client';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const successMessage = location.state?.message;

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await login({ username, password });
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', res.username);
      // Redirect to home
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Login failed, please check your credentials.');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '40px auto' }}>
      <h1 className="page-title fade-up" style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Iniciar Sesión</h1>
      {successMessage && <div className="alerta-badge alerta-VERDE fade-up" style={{ display: 'flex', justifyContent: 'center', marginBottom: '15px' }}>✓ {successMessage}</div>}
      {error && <div className="error-box fade-up-2">{error}</div>}
      
      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Tu usuario"
            />
          </div>
          
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="******"
            />
          </div>
        </div>
        
        <button className="btn btn-primary" type="submit" style={{ marginTop: '2rem' }}>
          Entrar
        </button>

        <p style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem', color: 'var(--muted)' }}>
          ¿No tienes cuenta? <Link to="/register" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Regístrate aquí</Link>
        </p>
      </form>
    </div>
  );
}
