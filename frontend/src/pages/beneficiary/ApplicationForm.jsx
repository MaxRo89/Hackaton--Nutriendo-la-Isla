import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import ReviewHistory from '../../components/applications/ReviewHistory';
import AppealForm from './AppealForm';

const empty = { zone: '', availability: '', household_size: '', frequency: '', transport: '', refrigeration: '', economic_context: '' };
const labels = { draft: 'Borrador', pending: 'Pendiente de revisión', information_requested: 'Información adicional solicitada', approved: 'Aprobada', rejected: 'No aprobada' };
const options = {
  frequency: { label: 'Frecuencia de necesidad', values: [['occasional', 'Ocasional'], ['weekly', 'Semanal'], ['daily', 'Diaria']] },
  transport: { label: 'Posibilidad de desplazarte al punto de recogida', values: [['yes', 'Sí'], ['limited', 'Con limitaciones'], ['no', 'No']] },
  refrigeration: { label: 'Disponibilidad de refrigeración', values: [['yes', 'Sí'], ['no', 'No']] },
};

export default function ApplicationForm({ onApplicationChange }) {
  const [application, setApplication] = useState(null);
  const [answers, setAnswers] = useState(empty);
  const [consent, setConsent] = useState(false);
  const [consentVersion, setConsentVersion] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [reload, setReload] = useState(0);
  const editable = !application || ['draft', 'pending', 'information_requested'].includes(application.status);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    api('/applications/me', { signal: controller.signal })
      .then((data) => {
        setApplication(data.application);
        onApplicationChange?.(data.application);
        setAnswers({ ...empty, ...data.application?.answers, household_size: data.application?.answers.household_size ?? '' });
        setConsentVersion(data.consent_version);
        setConsent(data.application?.consent_version === data.consent_version);
        setLoading(false);
      })
      .catch((failure) => { if (failure.name !== 'AbortError') { setError(failure.message); setLoading(false); } });
    return () => controller.abort();
  }, [reload]);

  function change(event) {
    setAnswers((previous) => ({ ...previous, [event.target.name]: event.target.value }));
    setNotice('Cambios sin guardar.');
  }

  async function save(event) {
    event.preventDefault();
    const action = event.nativeEvent.submitter?.value || 'save';
    setError('');
    setNotice('');
    setBusy(true);
    try {
      const data = await api('/applications/me', { method: 'POST', body: {
        answers: { ...answers, household_size: answers.household_size === '' ? null : Number(answers.household_size) },
        action, consent, consent_version: consentVersion, version: application?.version ?? 0,
      } });
      setApplication(data.application);
      onApplicationChange?.(data.application);
      setNotice(action === 'submit' ? 'Solicitud enviada. Queda pendiente de revisión humana.' : 'Borrador guardado. Puedes continuar después.');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  async function remove() {
    setBusy(true);
    setError('');
    try {
      await api('/applications/me', { method: 'DELETE', body: { version: application.version } });
      setApplication(null);
      onApplicationChange?.(null);
      setAnswers(empty);
      setConsent(false);
      setConfirmDelete(false);
      setNotice('Solicitud y respuestas eliminadas. Tu cuenta sigue activa.');
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  if (loading) return <p role="status">Cargando tu solicitud…</p>;
  if (!consentVersion) return <div className="alert alert-danger" role="alert">{error}<button className="btn btn-outline-dark ms-2" onClick={() => setReload(reload + 1)}>Reintentar</button></div>;

  return <section className="border-top pt-4 mt-4" aria-labelledby="application-title">
    <h3 id="application-title" className="h4">Solicitud de acceso</h3>
    <p>Estado: <strong>{application ? labels[application.status] : 'Sin solicitud'}</strong></p>
    {application?.submitted_at && <p className="small">Enviada: {new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Merida' }).format(new Date(application.submitted_at))}</p>}
    <p>Para enviar, indica solo tu zona y disponibilidad. Las demás respuestas son voluntarias y no determinan automáticamente tu acceso.</p>
    <button className="btn btn-outline-success mb-3" disabled={busy} onClick={() => { if (notice !== 'Cambios sin guardar.' || window.confirm('Se descartarán cambios sin guardar. ¿Continuar?')) { setNotice(''); setReload(reload + 1); } }}>Actualizar estado</button>
    <p className="small">Criterios de demo: consentimiento y claridad de zona y horario. Las preguntas opcionales no son criterios de exclusión. Puedes pedir revisión de una decisión no aprobada.</p>
    {application && <ReviewHistory application={application} />}
    {application && <AppealForm application={application} onSaved={(updated) => { setApplication(updated); onApplicationChange?.(updated); setNotice('Apelación enviada para revisión humana.'); }} />}
    {application?.status === 'pending' && <p className="alert alert-info">Tu solicitud espera revisión. Si guardas cambios como borrador, saldrá de la lista de pendientes hasta que vuelvas a enviarla.</p>}
    {application?.status === 'information_requested' && <p className="alert alert-info">Consulta el motivo de la revisión, corrige los datos solicitados y vuelve a enviar.</p>}
    {!editable && <p className="alert alert-info">Esta solicitud ya fue revisada. No puedes modificar la decisión desde el formulario.</p>}
    <form onSubmit={save}>
      <fieldset disabled={busy || !editable}>
        <legend className="h6">Datos para coordinar la recogida</legend>
        <div className="mb-3">
          <label htmlFor="zone" className="form-label">Colonia o zona aproximada (necesaria para enviar)</label>
          <input id="zone" name="zone" className="form-control" maxLength={120} value={answers.zone} onChange={change} aria-describedby="zone-help" />
          <p id="zone-help" className="form-text">No incluyas tu domicilio exacto. Usa datos ficticios en esta demo.</p>
        </div>
        <div className="mb-3">
          <label htmlFor="availability" className="form-label">Días y horarios de recogida (necesarios para enviar)</label>
          <textarea id="availability" name="availability" className="form-control" rows={2} maxLength={300} value={answers.availability} onChange={change} />
        </div>
        <div className="mb-3">
          <label htmlFor="household_size" className="form-label">Personas del hogar (opcional)</label>
          <input id="household_size" name="household_size" className="form-control" type="number" min={1} max={100} step={1} value={answers.household_size} onChange={change} />
        </div>
        {Object.entries(options).map(([name, option]) => <div className="mb-3" key={name}>
          <label htmlFor={name} className="form-label">{option.label} (opcional)</label>
          <select id={name} name={name} className="form-select" value={answers[name]} onChange={change}>
            <option value="">Prefiero no responder</option>
            {option.values.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>)}
        <div className="mb-3">
          <label htmlFor="economic_context" className="form-label">¿Quieres compartir algo sobre tu situación o necesidades? (opcional)</label>
          <textarea id="economic_context" name="economic_context" className="form-control" rows={3} maxLength={1000} value={answers.economic_context} onChange={change} aria-describedby="context-help" />
          <p id="context-help" className="form-text">Evita documentos de identidad, ingresos detallados y diagnósticos. No se utiliza para puntuar tu necesidad.</p>
        </div>
        <div className="bg-light border rounded p-3 mb-3" id="consent-notice">
          <h4 className="h6">Uso de tus respuestas · demo local</h4>
          <p>Se guardan en esta computadora para preparar tu solicitud y coordinar necesidades de recogida. Solo tú y el equipo revisor autorizado podrán consultarlas; no se compartirán con restaurantes ni otros beneficiarios. No se envían a servicios de IA.</p>
          <p>La participación es voluntaria. Puedes guardar un borrador incompleto. El envío requiere consentimiento, zona y disponibilidad; la decisión será humana. En esta fase puedes eliminar tu solicitud y sus respuestas sin borrar tu cuenta. Los datos permanecen localmente hasta que los elimines; utiliza únicamente información ficticia.</p>
          <div className="form-check">
            <input id="application-consent" className="form-check-input" type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} aria-describedby="consent-notice" />
            <label htmlFor="application-consent" className="form-check-label">He leído y acepto este uso de mis respuestas.</label>
          </div>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <button className="btn btn-outline-success" type="submit" value="save">Guardar borrador</button>
          <button className="btn btn-success" type="submit" value="submit">Enviar para revisión</button>
        </div>
      </fieldset>
    </form>
    {busy && <p className="mt-3" role="status">Guardando cambios…</p>}
    {notice && <p className="mt-3" role="status">{notice}</p>}
    {error && <div className="alert alert-danger mt-3" role="alert">{error}<button className="btn btn-outline-dark ms-2" disabled={busy} onClick={() => { if (window.confirm('Se descartarán los cambios sin guardar. ¿Recargar?')) setReload(reload + 1); }}>Recargar solicitud</button></div>}
    {application && editable && <div className="mt-4">
      {!confirmDelete ? <button className="btn btn-outline-danger" disabled={busy} onClick={() => setConfirmDelete(true)}>Eliminar solicitud y respuestas</button> : <div className="alert alert-warning">
        <p>Se eliminarán tus respuestas y se retirará tu solicitud. Tu cuenta se conservará. Esta acción no se puede deshacer.</p>
        <button className="btn btn-danger me-2" disabled={busy} onClick={remove}>Confirmar eliminación</button>
        <button className="btn btn-outline-dark" disabled={busy} onClick={() => setConfirmDelete(false)}>Cancelar</button>
      </div>}
    </div>}
  </section>;
}
