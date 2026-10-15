import { useEffect, useState } from 'react';
import { api } from '../../api/client';

const profileFields = [['display_name', 'Nombre del restaurante ficticio', 120], ['contact', 'Contacto ficticio', 200], ['pickup_label', 'Referencia del punto de recogida', 200]];
const donationFields = [['title', 'Nombre del alimento', 120], ['description', 'Descripción', 1000], ['allergens', 'Alérgenos declarados', 500], ['storage_notes', 'Conservación y requisitos de transporte', 500], ['handling_notes', 'Manipulación y estado del envase', 500]];
const initialProfile = { display_name: '', contact: '', pickup_label: '', pickup_lat: '', pickup_lng: '', version: 0 };
const initialDonation = { title: '', description: '', quantity: '', unit: 'pieza', food_category: 'panaderia', allergens: '', storage_notes: '', handling_notes: '', prepared_at: '', pickup_deadline: '', safety_confirmed: false };
const statusLabels = { available: 'Disponible', cancelled: 'Cancelada', expired: 'Vencida', exhausted: 'Agotada' };

function DonationRequestsList({ donation, onDonationUpdated }) {
  const [requests, setRequests] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  async function loadRequests() {
    setLoading(true);
    setError('');
    try {
      const data = await api(`/restaurant/donations/${donation.id}/requests`);
      setRequests(data.requests || []);
      setOpen(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function confirmRequest(req) {
    setBusyId(req.id);
    setError('');
    try {
      const data = await api(`/requests/${req.id}/confirm`, {
        method: 'POST',
        body: { version: req.version },
      });
      setRequests((prev) =>
        prev.map((item) => (item.id === req.id ? data.request : item))
      );
      if (data.donation) onDonationUpdated(data.donation);
    } catch (err) {
      setError(`Error al confirmar entrega: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  async function rejectRequest(req) {
    if (!window.confirm('¿Deseas rechazar esta solicitud de reserva?')) return;
    setBusyId(req.id);
    setError('');
    try {
      const data = await api(`/requests/${req.id}/reject`, {
        method: 'POST',
        body: { version: req.version },
      });
      setRequests((prev) =>
        prev.map((item) => (item.id === req.id ? data.request : item))
      );
    } catch (err) {
      setError(`Error al rechazar: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mt-3 pt-2 border-top">
      {error && <div className="alert alert-danger py-1 small">{error}</div>}
      {!open ? (
        <button
          type="button"
          className="btn btn-sm btn-outline-primary"
          onClick={loadRequests}
          disabled={loading}
        >
          {loading ? 'Consultando…' : 'Ver solicitudes de beneficiarios'}
        </button>
      ) : (
        <div>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <strong className="small text-success">
              Solicitudes recibidas ({requests.length})
            </strong>
            <button
              type="button"
              className="btn btn-sm btn-link text-decoration-none text-muted p-0"
              onClick={() => setOpen(false)}
            >
              Ocultar
            </button>
          </div>
          {requests.length === 0 ? (
            <p className="small text-muted mb-0">No hay solicitudes registradas para esta donación.</p>
          ) : (
            <div className="list-group list-group-flush small">
              {requests.map((req) => {
                const isPending = req.status === 'pending';
                const badgeColor =
                  req.status === 'confirmed'
                    ? 'bg-success'
                    : req.status === 'pending'
                    ? 'bg-warning text-dark'
                    : 'bg-secondary';
                const statusName =
                  req.status === 'confirmed'
                    ? 'Confirmada'
                    : req.status === 'pending'
                    ? 'Pendiente'
                    : req.status === 'rejected'
                    ? 'Rechazada'
                    : 'Cancelada';

                return (
                  <div key={req.id} className="list-group-item px-0 py-2">
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <span>
                        <strong>{req.quantity} {req.unit}</strong> solicitadas
                      </span>
                      <span className={`badge ${badgeColor}`}>{statusName}</span>
                    </div>
                    {req.notes && <p className="mb-1 text-muted">Nota: {req.notes}</p>}
                    {isPending && (
                      <div className="d-flex gap-2 mt-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-success py-0 px-2"
                          disabled={busyId === req.id}
                          onClick={() => confirmRequest(req)}
                        >
                          {busyId === req.id ? 'Confirmando…' : 'Confirmar entrega'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger py-0 px-2"
                          disabled={busyId === req.id}
                          onClick={() => rejectRequest(req)}
                        >
                          Rechazar
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RestaurantPanel({ authorized }) {
  const [profile, setProfile] = useState(initialProfile);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileDirty, setProfileDirty] = useState(false);
  const [donation, setDonation] = useState(initialDonation);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [aiHints, setAiHints] = useState([]);
  const [aiMessage, setAiMessage] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    Promise.all([api('/restaurant/profile', { signal: controller.signal }), authorized ? api('/restaurant/donations', { signal: controller.signal }) : Promise.resolve({ donations: [] })])
      .then(([data, list]) => { setProfile(data.profile || initialProfile); setProfileSaved(Boolean(data.profile)); setProfileDirty(false); setItems(list.donations); })
      .catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [authorized, refresh]);

  async function saveProfile(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const data = await api('/restaurant/profile', { method: 'PUT', body: { ...profile, pickup_lat: Number(profile.pickup_lat), pickup_lng: Number(profile.pickup_lng) } });
      setProfile(data.profile); setProfileSaved(true); setProfileDirty(false); setNotice('Perfil guardado. Las publicaciones existentes conservan su punto original.');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  const canCheckDonationHints = Boolean(
    donation.title &&
      donation.description &&
      donation.allergens &&
      donation.storage_notes &&
      donation.handling_notes &&
      donation.food_category &&
      donation.quantity &&
      donation.pickup_deadline &&
      (donation.food_category !== 'preparada' || donation.prepared_at)
  );

  async function verifyDonationHints() {
    setAiLoading(true);
    setAiMessage('');
    setAiHints([]);
    try {
      const data = await api('/ai/donation-hints', {
        method: 'POST',
        body: {
          title: donation.title,
          description: donation.description,
          allergens: donation.allergens,
          storage_notes: donation.storage_notes,
          handling_notes: donation.handling_notes,
          food_category: donation.food_category,
        },
      });
      const hints = Array.isArray(data.hints) ? data.hints : [];
      setAiHints(hints);
      setAiMessage(hints.length ? 'Se revisaron puntos pendientes para completar la donación.' : '✓ La información parece completa');
    } catch (failure) {
      setAiHints([]);
      setAiMessage('✓ La información parece completa');
    } finally {
      setAiLoading(false);
    }
  }

  async function publish(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const data = await api('/donations', { method: 'POST', body: { ...donation,
        prepared_at: donation.prepared_at ? new Date(`${donation.prepared_at}-06:00`).toISOString() : null,
        pickup_deadline: new Date(`${donation.pickup_deadline}-06:00`).toISOString(),
      } });
      setItems((previous) => [data.donation, ...previous]); setDonation(initialDonation); setNotice('Donación ficticia publicada.');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  async function cancel(item) {
    if (!window.confirm(`¿Cancelar la donación «${item.title}»? Se conservará en el historial.`)) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const data = await api(`/donations/${item.id}/cancel`, { method: 'POST', body: { version: item.version } });
      setItems((previous) => previous.map((entry) => entry.id === item.id ? data.donation : entry)); setNotice('Donación cancelada; se conserva el registro.');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  const updateProfile = (event) => { setProfile((previous) => ({ ...previous, [event.target.name]: event.target.value })); setProfileDirty(true); };
  const updateDonation = (event) => setDonation((previous) => ({ ...previous, [event.target.name]: event.target.value }));

  return <section className="border-top mt-4 pt-4">
    <h3 className="h4">Mi restaurante</h3>
    <p>Utiliza un comercio, contacto y punto aproximado ficticios. No incluyas domicilios de beneficiarios.</p>
    <button className="btn btn-outline-success mb-3" disabled={busy || loading} onClick={() => { if (!profileDirty || window.confirm('Se descartarán cambios del perfil sin guardar. ¿Actualizar?')) setRefresh(refresh + 1); }}>Actualizar perfil y donaciones</button>
    {notice && <p role="status" className="alert alert-success">{notice}</p>}
    {error && <p role="alert" className="alert alert-danger">{error}</p>}
    {loading ? <p role="status">Cargando restaurante…</p> : <>
      <form onSubmit={saveProfile}>
        <fieldset disabled={busy}>
          <legend className="h5">Perfil y punto de recogida</legend>
          {profileFields.map(([name, label, max]) => <div className="mb-3" key={name}><label className="form-label" htmlFor={name}>{label}</label><input id={name} name={name} className="form-control" required maxLength={max} value={profile[name]} onChange={updateProfile} /></div>)}
          <p className="form-text">Coordenadas aproximadas del comercio. El mapa interactivo se incorpora en la fase 6.</p>
          <div className="row">
            {[['pickup_lat', 'Latitud', -90, 90], ['pickup_lng', 'Longitud', -180, 180]].map(([name, label, min, max]) => <div className="col-sm-6 mb-3" key={name}><label className="form-label" htmlFor={name}>{label}</label><input id={name} name={name} className="form-control" type="number" step="any" min={min} max={max} required value={profile[name]} onChange={updateProfile} /></div>)}
          </div>
          <button className="btn btn-success">Guardar perfil</button>
        </fieldset>
      </form>
      {authorized ? <>
        <form onSubmit={publish} className="border-top mt-4 pt-4">
          <fieldset disabled={busy || !profileSaved || profileDirty}>
            <legend className="h5">Publicar donación ficticia</legend>
            {(!profileSaved || profileDirty) && <p>Guarda el perfil y su ubicación antes de publicar.</p>}
            {donationFields.map(([name, label, max]) => <div className="mb-3" key={name}><label className="form-label" htmlFor={name}>{label}</label><textarea id={name} name={name} className="form-control" rows={name === 'title' ? 1 : 2} maxLength={max} required value={donation[name]} onChange={updateDonation} /></div>)}
            <div className="row">
              <div className="col-sm-6 mb-3"><label htmlFor="quantity" className="form-label">Cantidad</label><input id="quantity" name="quantity" className="form-control" type="number" required min={donation.unit === 'kg' ? '.001' : '1'} max="100000" step={donation.unit === 'kg' ? '.001' : '1'} value={donation.quantity} onChange={updateDonation} /></div>
              <div className="col-sm-6 mb-3"><label htmlFor="unit" className="form-label">Unidad</label><select id="unit" name="unit" className="form-select" value={donation.unit} onChange={updateDonation}><option value="pieza">Piezas</option><option value="porcion">Porciones</option><option value="kg">Kilogramos</option></select></div>
            </div>
            <div className="mb-3"><label htmlFor="food_category" className="form-label">Categoría</label><select id="food_category" name="food_category" className="form-select" value={donation.food_category} onChange={updateDonation}><option value="panaderia">Panadería</option><option value="envasado">Envasado</option><option value="preparada">Comida preparada</option><option value="fresco">Producto fresco</option></select></div>
            <p className="form-text">Fechas y horas de Ciudad del Carmen (UTC−6).</p>
            <div className="mb-3"><label htmlFor="prepared_at" className="form-label">Preparación (obligatoria para comida preparada)</label><input id="prepared_at" name="prepared_at" className="form-control" type="datetime-local" required={donation.food_category === 'preparada'} value={donation.prepared_at} onChange={updateDonation} /></div>
            <div className="mb-3"><label htmlFor="pickup_deadline" className="form-label">Límite de recogida</label><input id="pickup_deadline" name="pickup_deadline" className="form-control" type="datetime-local" required value={donation.pickup_deadline} onChange={updateDonation} /></div>
            <div className="alert alert-warning">Demo sin distribución real. Completar los campos no certifica inocuidad. Para operar con alimentos reales se necesitan protocolos y revisión por responsables capacitados.</div>
            <div className="form-check mb-3"><input id="safety_confirmed" className="form-check-input" type="checkbox" required checked={donation.safety_confirmed} onChange={(e) => setDonation((previous) => ({ ...previous, safety_confirmed: e.target.checked }))} /><label htmlFor="safety_confirmed" className="form-check-label">Revisé los datos ficticios de manipulación, envase, conservación, alérgenos y horario. No hay información crítica pendiente en esta simulación.</label></div>
            <div className="d-flex flex-wrap gap-2 mt-3">
              {canCheckDonationHints && (
                <button type="button" className="btn btn-outline-primary" disabled={aiLoading || busy} onClick={verifyDonationHints}>
                  {aiLoading ? 'Verificando…' : 'Verificar con IA'}
                </button>
              )}
              <button className="btn btn-success">Publicar donación</button>
            </div>
            {aiMessage && (
              <div className={`alert mt-3 ${aiHints.length ? 'alert-info' : 'alert-success'}`} role="status">
                {aiHints.length ? (
                  <>
                    <strong>Revisión de IA</strong>
                    <ul className="mb-0 mt-2 ps-3">
                      {aiHints.map((hint, index) => <li key={`${hint}-${index}`}>{hint}</li>)}
                    </ul>
                  </>
                ) : (
                  '✓ La información parece completa'
                )}
              </div>
            )}
          </fieldset>
        </form>
        <section className="border-top mt-4 pt-4"><h4 className="h5">Mis donaciones</h4>
          {!items.length && <p>Aún no hay donaciones publicadas.</p>}
          {items.map((item) => {
            const status = item.status === 'available' && new Date(item.pickup_deadline) <= new Date() ? 'expired' : item.status;
            const remaining = item.remaining_quantity || item.quantity;
            return <article className="border rounded p-3 mb-3 bg-white" key={item.id}>
              <h5>{item.title} <span className="badge text-bg-secondary">{statusLabels[status] || status}</span></h5>
              <p className="mb-1">
                <strong>Existencias:</strong> {remaining} {item.unit} disponibles (Publicadas: {item.quantity})
              </p>
              <p className="mb-1">{item.description}</p>
              <p className="small text-muted mb-2">Recogida: {item.pickup.pickup_label} · {new Date(item.pickup_deadline).toLocaleString('es-MX', { timeZone: 'America/Merida' })}</p>
              {status === 'available' && <button className="btn btn-outline-danger btn-sm mb-2" disabled={busy} onClick={() => cancel(item)}>Cancelar donación</button>}
              <DonationRequestsList
                donation={item}
                onDonationUpdated={(updated) => {
                  setItems((prev) => prev.map((entry) => entry.id === updated.id ? updated : entry));
                }}
              />
            </article>;
          })}
        </section>
      </> : <p className="alert alert-info mt-3">Puedes guardar tu perfil. Para publicar, utiliza el restaurante ficticio preautorizado de la demo.</p>}
    </>}
  </section>;
}
