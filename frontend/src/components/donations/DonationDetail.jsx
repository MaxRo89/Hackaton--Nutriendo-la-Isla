import { useState } from 'react';
import { api } from '../../api/client';

const categoryLabels = {
  panaderia: 'Panadería',
  envasado: 'Envasado',
  preparada: 'Comida preparada',
  fresco: 'Producto fresco',
};

const unitLabels = {
  pieza: 'piezas',
  porcion: 'porciones',
  kg: 'kg',
};

function formatQuantity(quantityStr, unit) {
  if (!quantityStr) return '0';
  if (unit === 'kg') return `${quantityStr} kg`;
  const integerPart = quantityStr.split('.')[0];
  return `${integerPart} ${unitLabels[unit] || unit}`;
}

function formatDate(isoString) {
  if (!isoString) return 'No aplica';
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'America/Merida',
  }).format(new Date(isoString));
}

export default function DonationDetail({ donation, onClose, onRequestSuccess }) {
  const [quantity, setQuantity] = useState(
    donation?.unit === 'kg' ? '1.000' : '1'
  );
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  if (!donation) return null;

  const remaining = donation.remaining_quantity || donation.quantity;
  const isAvailable = donation.status === 'available' && parseFloat(remaining) > 0;

  async function submitRequest(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await api(`/donations/${donation.id}/requests`, {
        method: 'POST',
        body: {
          quantity: String(quantity),
          notes: notes.trim() || undefined,
        },
      });
      setNotice('¡Solicitud de reserva enviada con éxito! El restaurante revisará tu petición.');
      onRequestSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="card border-0 shadow-lg mb-4"
      role="region"
      aria-labelledby="detail-donation-title"
    >
      <div className="card-header bg-success text-white d-flex justify-content-between align-items-center py-3">
        <h4 id="detail-donation-title" className="h5 mb-0">
          Detalle del alimento · {donation.title}
        </h4>
        <button
          type="button"
          className="btn-close btn-close-white"
          aria-label="Cerrar detalle"
          onClick={onClose}
        />
      </div>
      <div className="card-body p-4">
        {notice && <div className="alert alert-success" role="status">{notice}</div>}
        {error && <div className="alert alert-danger" role="alert">{error}</div>}

        <div className="row g-4">
          <div className="col-md-7">
            <div className="mb-3">
              <span className="badge bg-secondary me-2">
                {categoryLabels[donation.food_category] || donation.food_category}
              </span>
              <span className={`badge ${isAvailable ? 'bg-success' : 'bg-warning text-dark'}`}>
                {isAvailable ? 'Disponible' : 'Agotada / No disponible'}
              </span>
            </div>

            <h5 className="h6 text-muted mb-1">Descripción</h5>
            <p className="lead fs-6">{donation.description}</p>

            <div className="row g-3 my-2">
              <div className="col-sm-6">
                <div className="p-3 bg-light rounded">
                  <span className="text-muted small d-block">Existencias disponibles</span>
                  <strong className="fs-5 text-success">
                    {formatQuantity(remaining, donation.unit)}
                  </strong>
                  <small className="text-muted d-block">
                    Total publicado: {formatQuantity(donation.quantity, donation.unit)}
                  </small>
                </div>
              </div>
              <div className="col-sm-6">
                <div className="p-3 bg-light rounded">
                  <span className="text-muted small d-block">Límite de recogida</span>
                  <strong className="fs-6 text-danger">
                    {formatDate(donation.pickup_deadline)}
                  </strong>
                </div>
              </div>
            </div>

            {donation.prepared_at && (
              <p className="small mb-2">
                <strong>Fecha/hora de preparación:</strong> {formatDate(donation.prepared_at)}
              </p>
            )}

            <hr className="my-3" />

            <h5 className="h6 text-dark fw-bold mb-2">Información alimentaria y de seguridad</h5>
            <ul className="list-group list-group-flush mb-3">
              <li className="list-group-item px-0">
                <strong>Alérgenos declarados:</strong> {donation.allergens}
              </li>
              <li className="list-group-item px-0">
                <strong>Conservación y transporte:</strong> {donation.storage_notes}
              </li>
              <li className="list-group-item px-0">
                <strong>Manipulación y envase:</strong> {donation.handling_notes}
              </li>
            </ul>

            {/* Formulario de reserva fase 7 */}
            {isAvailable && !notice && (
              <div className="card border-success mt-4">
                <div className="card-header bg-light text-success fw-bold">
                  Solicitar reserva de este alimento
                </div>
                <div className="card-body">
                  <form onSubmit={submitRequest}>
                    <div className="mb-3">
                      <label htmlFor="req-qty" className="form-label fw-semibold">
                        Cantidad a solicitar ({unitLabels[donation.unit] || donation.unit})
                      </label>
                      <input
                        id="req-qty"
                        type="number"
                        className="form-control"
                        required
                        min={donation.unit === 'kg' ? '.001' : '1'}
                        max={parseFloat(remaining)}
                        step={donation.unit === 'kg' ? '.001' : '1'}
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        disabled={busy}
                      />
                      <small className="form-text text-muted">
                        Puedes solicitar una cantidad parcial o el total disponible.
                      </small>
                    </div>
                    <div className="mb-3">
                      <label htmlFor="req-notes" className="form-label fw-semibold">
                        Nota para la recogida (opcional)
                      </label>
                      <textarea
                        id="req-notes"
                        className="form-control"
                        rows={2}
                        maxLength={500}
                        placeholder="Ej. Puedo pasar en bicicleta hoy a las 5:00 PM."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        disabled={busy}
                      />
                    </div>
                    <button
                      type="submit"
                      className="btn btn-success w-100"
                      disabled={busy}
                    >
                      {busy ? 'Enviando solicitud…' : 'Confirmar solicitud de reserva'}
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>

          <div className="col-md-5">
            <div className="border rounded p-3 bg-light">
              <h5 className="h6 text-success fw-bold mb-3">Punto de recogida</h5>
              <p className="mb-1">
                <strong>Comercio donante:</strong> {donation.pickup?.display_name || 'Restaurante'}
              </p>
              <p className="mb-1">
                <strong>Referencia de recogida:</strong> {donation.pickup?.pickup_label || 'Punto acordado'}
              </p>
              <p className="mb-1">
                <strong>Contacto de coordinación:</strong> {donation.pickup?.contact || 'Sin contacto'}
              </p>
              <p className="small text-muted mb-0">
                <strong>Coordenadas aproximadas:</strong> {donation.pickup?.pickup_lat?.toFixed(4)},{' '}
                {donation.pickup?.pickup_lng?.toFixed(4)}
              </p>
            </div>

            <div className="alert alert-info mt-3 small" role="note">
              <strong>Fase 7 activa:</strong> Una vez enviada tu solicitud, el comercio la revisará y confirmará la entrega. No acudas antes de la confirmación o fuera del límite de recogida.
            </div>

            <button
              type="button"
              className="btn btn-outline-secondary w-100 mt-2"
              onClick={onClose}
            >
              Volver al listado
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
