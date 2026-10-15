import { useState } from 'react';
import { api } from '../../api/client';

export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [role, setRole] = useState('beneficiary');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function changeMode(next) {
    setMode(next);
    setError('');
    setPassword('');
    setConfirmation('');
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (mode === 'register' && password !== confirmation) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setBusy(true);
    try {
      const body = { email, password };
      if (mode === 'register') body.role = role;
      const data = await api(`/auth/${mode}`, { method: 'POST', body });
      setPassword('');
      setConfirmation('');
      onAuthenticated(data.user);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card border-0 shadow-sm" aria-labelledby="auth-heading">
      <div className="card-body p-4">
        <div className="d-flex gap-2 mb-4">
          <button type="button" className={`btn ${mode === 'login' ? 'btn-success' : 'btn-outline-success'}`} aria-pressed={mode === 'login'} disabled={busy} onClick={() => changeMode('login')}>Iniciar sesión</button>
          <button type="button" className={`btn ${mode === 'register' ? 'btn-success' : 'btn-outline-success'}`} aria-pressed={mode === 'register'} disabled={busy} onClick={() => changeMode('register')}>Crear cuenta</button>
        </div>
        <h2 id="auth-heading" className="h4">{mode === 'login' ? 'Qué gusto verte' : 'Únete a Nutriendo la Isla'}</h2>
        <p className="text-secondary">Demo local: utiliza únicamente datos ficticios.</p>
        <form onSubmit={submit}>
          <fieldset disabled={busy}>
            {mode === 'register' && <div className="mb-3">
              <label htmlFor="role" className="form-label">Tipo de cuenta</label>
              <select id="role" className="form-select" value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="beneficiary">Persona beneficiaria</option>
                <option value="restaurant">Restaurante</option>
              </select>
              <p className="form-text">{role === 'beneficiary' ? 'Crear tu cuenta no equivale a la aprobación para solicitar alimentos.' : 'La demo usa restaurantes ficticios preautorizados. Una cuenta nueva quedará sin autorización.'}</p>
            </div>}
            <div className="mb-3">
              <label htmlFor="email" className="form-label">Correo electrónico</label>
              <input id="email" className="form-control" type="email" autoComplete="username" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} />
            </div>
            <div className="mb-3">
              <label htmlFor="password" className="form-label">Contraseña</label>
              <input id="password" className="form-control" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={12} maxLength={128} aria-describedby="password-help" value={password} onChange={(event) => setPassword(event.target.value)} />
              <div id="password-help" className="form-text">Entre 12 y 128 caracteres.</div>
            </div>
            {mode === 'register' && <div className="mb-3">
              <label htmlFor="confirmation" className="form-label">Repetir contraseña</label>
              <input id="confirmation" className="form-control" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
            </div>}
            {error && <p className="alert alert-danger" role="alert">{error}</p>}
            <button className="btn btn-success w-100" type="submit">{busy ? 'Espera un momento…' : mode === 'login' ? 'Entrar' : 'Registrarme'}</button>
          </fieldset>
        </form>
        {mode === 'login' && <p className="small text-secondary mt-3 mb-0">El equipo revisor utiliza este mismo acceso con su cuenta interna.</p>}
      </div>
    </section>
  );
}
