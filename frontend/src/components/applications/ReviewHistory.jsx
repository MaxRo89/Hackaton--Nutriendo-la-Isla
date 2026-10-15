export const statusLabels = { draft: 'Borrador', pending: 'Pendiente de revisión', information_requested: 'Información adicional solicitada', approved: 'Aprobada', rejected: 'No aprobada' };

export default function ReviewHistory({ application }) {
  if (!application?.reviews?.length && !application?.appeals?.length) return null;
  return <div className="my-3">
    <h4 className="h6">Decisiones y apelaciones</h4>
    {application.reviews.map((review) => <div className="border rounded p-3 mb-2" key={review.id}>
      <strong>{statusLabels[review.decision]}</strong>
      <p className="small text-secondary mb-1">{new Date(review.reviewed_at).toLocaleString('es-MX', { timeZone: 'America/Merida' })}</p>
      <p className="mb-0 text-break" style={{ whiteSpace: 'pre-wrap' }}>{review.reason}</p>
    </div>)}
    {application.appeals.map((appeal) => <div className="border rounded p-3 mb-2" key={appeal.id}>
      <strong>Apelación {appeal.status === 'pending' ? 'pendiente' : 'resuelta'}</strong>
      <p className="mb-0 text-break" style={{ whiteSpace: 'pre-wrap' }}>{appeal.message}</p>
      {appeal.resolution_review_id && <p className="small mb-0">Resuelta mediante decisión #{appeal.resolution_review_id}.</p>}
    </div>)}
  </div>;
}
