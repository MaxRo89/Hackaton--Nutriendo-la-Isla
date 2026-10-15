import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import ReviewHistory, { statusLabels } from '../../components/applications/ReviewHistory';

const fields = { zone: 'Zona', availability: 'Disponibilidad', household_size: 'Personas del hogar', frequency: 'Frecuencia', transport: 'Transporte', refrigeration: 'Refrigeración', economic_context: 'Contexto voluntario' };
const values = { yes: 'Sí', no: 'No', limited: 'Con limitaciones', occasional: 'Ocasional', weekly: 'Semanal', daily: 'Diaria' };

function ReviewCard({ application, onSaved }) {
  const [decision, setDecision] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiSummary, setAiSummary] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const canReview = application.status === 'pending' || (application.status === 'rejected' && application.appeals.some((a) => a.status === 'pending'));
  async function generateSummary() {
    setAiLoading(true);
    setAiSummary('');
    try {
      const data = await api('/ai/application-summary', { method: 'POST', body: { answers: application.answers || {} } });
      setAiSummary(data.summary || '');
    } catch {
      setAiSummary('');
    } finally {
      setAiLoading(false);
    }
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const data = await api(`/reviewer/applications/${application.id}`, { method: 'PATCH', body: { version: application.version, decision, reason } });
      onSaved(data.application);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <article className="border rounded p-3 mb-3">
    <h4 className="h5">Solicitud #{application.id} · {statusLabels[application.status]}</h4>
    <dl>{Object.entries(fields).map(([key, label]) => <div key={key} className="mb-2">
      <dt>{label}</dt><dd className="mb-0 text-break" style={{ whiteSpace: 'pre-wrap' }}>{values[application.answers[key]] || application.answers[key] || 'Sin respuesta (opcional)'}</dd>
    </div>)}</dl>
    <div className="d-flex justify-content-end mb-3">
      <button type="button" className="btn btn-outline-primary btn-sm" onClick={generateSummary} disabled={aiLoading || busy}>
        {aiLoading ? 'Generando…' : 'Generar resumen IA'}
      </button>
    </div>
    {aiSummary && (
      <div className="alert alert-light border border-primary-subtle mb-3" role="note">
        <div className="d-flex align-items-center gap-2 mb-2">
          <span aria-hidden="true" className="fs-5">✦</span>
          <strong>Resumen IA</strong>
        </div>
        <p className="mb-2">{aiSummary}</p>
        <small className="text-muted">Resumen generado automáticamente · No sustituye la revisión humana</small>
      </div>
    )}
    <ReviewHistory application={application} />
    {canReview && <form onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend className="h6">{application.status === 'rejected' ? 'Resolver apelación' : 'Revisar solicitud'}</legend>
        <label className="form-label" htmlFor={`decision-${application.id}`}>Decisión humana</label>
        <select id={`decision-${application.id}`} className="form-select mb-3" required value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="">Selecciona una decisión</option>
          <option value="approved">Aprobar</option><option value="information_requested">Solicitar información adicional</option><option value="rejected">No aprobar (permite apelación)</option>
        </select>
        <label className="form-label" htmlFor={`reason-${application.id}`}>Motivo visible para la persona solicitante</label>
        <textarea id={`reason-${application.id}`} className="form-control mb-3" required maxLength={1000} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        <button className="btn btn-success">{busy ? 'Guardando…' : 'Registrar decisión'}</button>
      </fieldset>
      {error && <p role="alert" className="alert alert-danger mt-3">{error}</p>}
    </form>}
  </article>;
}

export default function ReviewerPanel() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState('actionable');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    api('/reviewer/applications', { signal: controller.signal }).then((data) => setApplications(data.applications))
      .catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reload]);
  const shown = applications.filter((a) => filter === 'all' || a.status === 'pending' || a.appeals.some((item) => item.status === 'pending'));
  return <section className="border-top mt-4 pt-4" aria-labelledby="review-title">
    <h3 className="h4" id="review-title">Revisión de solicitudes</h3>
    <p className="alert alert-info">Demo: revisa consentimiento y claridad de zona y horario. Pide aclaraciones concretas cuando falte información. No uses las respuestas opcionales, la redacción ni la situación económica para puntuar merecimiento. Toda decisión debe explicar su motivo; una decisión desfavorable permite apelar.</p>
    <div className="d-flex flex-wrap gap-2 mb-3">
      <label htmlFor="review-filter" className="visually-hidden">Mostrar solicitudes</label>
      <select id="review-filter" className="form-select w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="actionable">Pendientes y apelaciones</option><option value="all">Todos los envíos</option></select>
      <button className="btn btn-outline-success" disabled={loading} onClick={() => { setNotice(''); setReload(reload + 1); }}>Actualizar</button>
    </div>
    {notice && <p role="status">{notice}</p>}
    {loading ? <p role="status">Cargando solicitudes…</p> : error ? <p className="alert alert-danger" role="alert">{error}</p> : shown.length ? shown.map((application) => <ReviewCard key={`${application.id}-${application.version}`} application={application} onSaved={(updated) => { setApplications((items) => items.map((item) => item.id === updated.id ? updated : item)); setNotice('Decisión registrada y visible para la persona solicitante.'); }} />) : <p>No hay solicitudes en esta vista.</p>}
  </section>;
}
