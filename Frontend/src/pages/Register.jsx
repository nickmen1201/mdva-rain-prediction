import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../api/client';

export default function Register() {
  const [formData, setFormData] = useState({
    nombre: '',
    username: '',
    email: '',
    password: '',
    fechaNacimiento: '',
    idBarrio: 0
  });
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        idBarrio: parseInt(formData.idBarrio) || null
      };
      const res = await register(payload);
      navigate('/login', { state: { message: 'Registro exitoso, ya puedes iniciar sesión' } });
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Registration failed.');
    }
  };

  return (
    <div style={{ maxWidth: '450px', margin: '40px auto' }}>
      <h1 className="page-title fade-up" style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Registro</h1>
      {error && <div className="error-box fade-up-2">{error}</div>}
      
      <form onSubmit={handleSubmit} className="card fade-up-2">
        <div className="form-grid">
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Nombre</label>
            <input type="text" name="nombre" required value={formData.nombre} onChange={handleChange} placeholder="Tu nombre..." />
          </div>
          
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Username</label>
            <input type="text" name="username" required value={formData.username} onChange={handleChange} placeholder="Nombre de usuario" />
          </div>
          
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Email</label>
            <input type="email" name="email" required value={formData.email} onChange={handleChange} placeholder="tu@email.com" />
          </div>
          
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Password</label>
            <input type="password" name="password" required value={formData.password} onChange={handleChange} placeholder="******" />
          </div>
          
          <div className="field" style={{ gridColumn: '1 / -1' }}>
            <label>Fecha de Nacimiento</label>
            <input type="date" name="fechaNacimiento" required value={formData.fechaNacimiento} onChange={handleChange} />
          </div>
        </div>
        
        <button className="btn btn-primary" type="submit" style={{ marginTop: '2rem' }}>
          Registrarme
        </button>
        
        <p style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem', color: 'var(--muted)' }}>
          ¿Ya tienes cuenta? <Link to="/login" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Inicia sesión aquí</Link>
        </p>
      </form>
    </div>
  );
}
