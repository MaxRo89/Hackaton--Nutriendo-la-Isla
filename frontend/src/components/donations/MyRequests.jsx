import { useEffect, useState } from 'react';
import { api } from '../../api/client';

const statusLabels = {
  pending: { label: 'Pendiente de confirmación', badge: 'bg-warning text-dark' },
  confirmed: { label: 'Confirmada · Lista para recogida', badge: 'bg-success' },
  cancelled: { label: 'Cancelada', badge: 'bg-secondary' },
  rejected: { label: 'No aceptada', badge: 'bg-danger' },
};

function formatDate(isoString) {
  if (!isoString) return '';
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Merida',
  }).format(new Date(isoString));
}

export default function MyRequests({ refreshTrigger }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  function loadRequests() {
    setLoading(true);
    setError('');
    api('/beneficiary/requests')
      .then((data) => setRequests(data.requests || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadRequests();
  }, [refreshTrigger]);

  async function cancelRequest(req) {
    if (!window.confirm('¿Deseas cancelar esta solicitud de reserva?')) return;
    setBusyId(req.id);
    try {
      const data = await api(`/requests/${req.id}/cancel`, {
        method: 'POST',
        body: { version: req.version },
      });
      setRequests((prev) =>
        prev.map((item) => (item.id === req.id ? data.request : item))
      );
    } catch (err) {
      alert(`Error al cancelar: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <p className="text-muted small">Cargando tus solicitudes…</p>;
  if (error) return <div className="alert alert-danger small">{error}</div>;
  if (requests.length === 0) {
    return (
      <div className="alert alert-light border small text-muted">
        Aún no has solicitado reservas de alimentos. Explora las donaciones disponibles en el mapa o listado y selecciona una para solicitarla.
      </div>
    );
  }

  return (
    <div className="mt-3">
      <h5 className="h6 text-success fw-bold mb-3">Mis solicitudes de reserva</h5>
      <div className="row g-3">
        {requests.map((req) => {
          const statusInfo = statusLabels[req.status] || {
            label: req.status,
            badge: 'bg-secondary',
          };
          const unitStr = req.unit === 'kg' ? 'kg' : (req.unit === 'pieza' ? 'piezas' : req.unit);

          return (
            <div key={req.id} className="col-12">
              <div className="border rounded p-3 bg-white shadow-sm">
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <h6 className="mb-0 fw-bold">{req.donation_title}</h6>
                  <span className={`badge ${statusInfo.badge}`}>
                    {statusInfo.label}
                  </span>
                </div>
                <p className="small mb-1">
                  <strong>Cantidad solicitada:</strong> {req.quantity} {unitStr}
                </p>
                {req.notes && (
                  <p className="small mb-1 text-muted">
                    <strong>Tu nota:</strong> {req.notes}
                  </p>
                )}
                {req.pickup && (
                  <p className="small mb-1 text-muted">
                    <strong>Lugar de recogida:</strong> {req.pickup.pickup_label} ({req.pickup.display_name})
                  </p>
                )}
                <div className="d-flex justify-content-between align-items-center mt-2 pt-2 border-top">
                  <small className="text-muted">
                    Solicitado: {formatDate(req.requested_at)}
                    {req.confirmed_at && ` · Confirmado: ${formatDate(req.confirmed_at)}`}
                  </small>
                  {req.status === 'pending' && (
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm"
                      disabled={busyId === req.id}
                      onClick={() => cancelRequest(req)}
                    >
                      {busyId === req.id ? 'Cancelando…' : 'Cancelar solicitud'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
