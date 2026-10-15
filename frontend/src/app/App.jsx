import { useEffect, useState } from 'react';
import { api } from '../api/client';
import AuthForm from '../pages/auth/AuthForm';
import AccountHome from '../pages/AccountHome';

export default function App() {
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    api('/auth/me', { signal: controller.signal })
      .then((data) => { setUser(data.user); setStatus('ready'); })
      .catch((error) => { if (error.name !== 'AbortError') setStatus(error.status === 401 ? 'ready' : 'error'); });
    return () => controller.abort();
  }, []);

  return (
    <>
      <header className="border-bottom bg-white">
        <div className="container py-3 fw-bold text-success">Nutriendo la Isla</div>
      </header>
      <main className="container py-5">
        <div className="row justify-content-center">
          <div className="col-lg-8">
            <p className="text-success fw-semibold">Ciudad del Carmen, Campeche</p>
            <h1 className="display-4 fw-bold">Compartir alimentos, conectar personas.</h1>
            <p className="lead my-4">Un espacio para conectar restaurantes con excedentes alimentarios y personas que buscan apoyo.</p>
            {status === 'loading' && <p role="status">Comprobando sesión…</p>}
            {status === 'error' && <div className="alert alert-danger" role="alert">No se pudo conectar con el servicio. <button className="btn btn-outline-dark ms-2" onClick={() => window.location.reload()}>Reintentar</button></div>}
            {status === 'ready' && (user ? <AccountHome user={user} onLogout={() => setUser(null)} /> : <AuthForm onAuthenticated={setUser} />)}
          </div>
        </div>
      </main>
    </>
  );
}
