import { useEffect, useState } from 'react';
import { api } from '../api/client';
import ApplicationForm from './beneficiary/ApplicationForm';
import ReviewerPanel from './reviewer/ReviewerPanel';
import RestaurantPanel from './restaurant/RestaurantPanel';
import DonationsBrowser from '../components/donations/DonationsBrowser';

const labels = { restaurant: 'Restaurante', beneficiary: 'Persona beneficiaria', reviewer: 'Revisor interno' };

export default function AccountHome({ user, onLogout }) {
  const [message, setMessage] = useState('Comprobando acceso…');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [beneficiaryApp, setBeneficiaryApp] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    api(`/${user.role}/access`, { signal: controller.signal })
      .then((data) => setMessage(data.message))
      .catch((failure) => { if (failure.name !== 'AbortError') setMessage(failure.message); });
    return () => controller.abort();
  }, [user.role]);

  useEffect(() => {
    if (user.role === 'beneficiary') {
      const controller = new AbortController();
      api('/applications/me', { signal: controller.signal })
        .then((data) => setBeneficiaryApp(data.application))
        .catch(() => {});
      return () => controller.abort();
    }
  }, [user.role]);

  async function logout() {
    setBusy(true);
    setError('');
    try {
      await api('/auth/logout', { method: 'POST' });
      onLogout();
    } catch (failure) {
      if (failure.status === 401) onLogout();
      else setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  const isApproved = user.role === 'beneficiary' && beneficiaryApp?.status === 'approved';

  return <section className="card border-0 shadow-sm">
    <div className="card-body p-4">
      <h2 className="h4">Mi cuenta · {labels[user.role]}</h2>
      <p className="text-break">{user.email}</p>
      <p className="alert alert-info" role="status">{message}</p>
      <p className="small text-secondary">Demostración local con datos ficticios.</p>
      {error && <p className="alert alert-danger" role="alert">{error}</p>}
      <button className="btn btn-outline-success" disabled={busy} onClick={logout}>{busy ? 'Cerrando sesión…' : 'Cerrar sesión'}</button>
      {isApproved && <DonationsBrowser />}
      {user.role === 'beneficiary' && <ApplicationForm onApplicationChange={setBeneficiaryApp} />}
      {user.role === 'reviewer' && <ReviewerPanel />}
      {user.role === 'restaurant' && <RestaurantPanel authorized={user.restaurant_authorized} />}
    </div>
  </section>;
}
