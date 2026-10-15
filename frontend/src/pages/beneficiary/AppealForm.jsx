import { useState } from 'react';
import { api } from '../../api/client';

export default function AppealForm({ application, onSaved }) {
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (application.status !== 'rejected' || application.appeals.some((item) => item.status === 'pending')) return null;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const data = await api('/applications/me/appeals', { method: 'POST', body: { message, version: application.version } });
      onSaved(data.application); setMessage('');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="border rounded p-3 my-3">
    <h4 className="h6">Solicitar revisión de la decisión</h4>
    <p>Puedes explicar tu desacuerdo o aportar una aclaración. Una persona revisará tu apelación; no cambia automáticamente la decisión.</p>
    <label className="form-label" htmlFor="appeal-message">Mensaje de apelación</label>
    <textarea id="appeal-message" className="form-control mb-3" required maxLength={1000} rows={3} disabled={busy} value={message} onChange={(event) => setMessage(event.target.value)} />
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    <button className="btn btn-outline-success" disabled={busy}>{busy ? 'Enviando…' : 'Enviar apelación'}</button>
  </form>;
}
