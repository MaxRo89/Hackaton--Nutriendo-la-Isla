import { useEffect, useState, useRef } from 'react';
import { api } from '../../api/client';
import DonationsMap from './DonationsMap';
import DonationDetail from './DonationDetail';
import MyRequests from './MyRequests';

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

export default function DonationsBrowser() {
  const [activeTab, setActiveTab] = useState('catalog'); // 'catalog' | 'requests'
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [detailDonation, setDetailDonation] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const detailRef = useRef(null);
  const cardRefs = useRef({});

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');

    api('/donations', { signal: controller.signal })
      .then((data) => {
        setDonations(data.donations || []);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [refreshIndex]);

  async function openDetail(donation) {
    setDetailLoading(true);
    setError('');
    try {
      const fresh = await api(`/donations/${donation.id}`);
      setDetailDonation(fresh.donation);
      setSelectedId(donation.id);
      setTimeout(() => {
        detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    } catch (err) {
      setError(`No se pudo consultar el detalle: ${err.message}`);
      if (err.status === 404) {
        setRefreshIndex((prev) => prev + 1);
      }
    } finally {
      setDetailLoading(false);
    }
  }

  function handleSelectOnMap(id) {
    setSelectedId(id);
    const cardEl = cardRefs.current[id];
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  return (
    <section className="border-top pt-4 mt-4" aria-labelledby="donations-browser-title">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h3 id="donations-browser-title" className="h4 text-success mb-1">
            Donaciones en Ciudad del Carmen
          </h3>
          <p className="text-muted small mb-0">
            Encuentra alimentos en el mapa o consulta el estado de tus reservas activas.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline-success btn-sm text-nowrap ms-2"
          disabled={loading || detailLoading}
          onClick={() => setRefreshIndex((prev) => prev + 1)}
        >
          {loading ? 'Actualizando…' : 'Actualizar'}
        </button>
      </div>

      {/* Tabs */}
      <ul className="nav nav-pills mb-3" role="tablist">
        <li className="nav-item" role="presentation">
          <button
            type="button"
            className={`nav-link ${activeTab === 'catalog' ? 'active bg-success' : 'text-success'}`}
            onClick={() => setActiveTab('catalog')}
          >
            🗺️ Alimentos disponibles ({donations.length})
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            type="button"
            className={`nav-link ${activeTab === 'requests' ? 'active bg-success' : 'text-success'}`}
            onClick={() => setActiveTab('requests')}
          >
            📋 Mis solicitudes de reserva
          </button>
        </li>
      </ul>

      {detailDonation && (
        <div ref={detailRef}>
          <DonationDetail
            donation={detailDonation}
            onClose={() => setDetailDonation(null)}
            onRequestSuccess={() => {
              setRefreshIndex((prev) => prev + 1);
            }}
          />
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="btn btn-outline-dark btn-sm ms-3"
            onClick={() => setRefreshIndex((prev) => prev + 1)}
          >
            Reintentar
          </button>
        </div>
      )}

      {activeTab === 'requests' ? (
        <MyRequests refreshTrigger={refreshIndex} />
      ) : loading ? (
        <div className="p-5 text-center text-muted" role="status">
          <div className="spinner-border text-success mb-2" role="status" aria-hidden="true" />
          <p className="mb-0">Cargando donaciones disponibles…</p>
        </div>
      ) : donations.length === 0 ? (
        <div className="alert alert-info py-4" role="status">
          <h4 className="h6 fw-bold mb-1">Sin donaciones disponibles en este momento</h4>
          <p className="mb-0 small">
            Actualmente no hay excedentes vigentes publicados en Ciudad del Carmen. Vuelve a consultar periódicamente cuando los comercios autorizados compartan nuevos alimentos.
          </p>
        </div>
      ) : (
        <>
          {/* Map view */}
          <DonationsMap
            donations={donations}
            selectedId={selectedId}
            onSelectDonation={handleSelectOnMap}
            onOpenDetail={openDetail}
          />

          {/* Accessible coordinated list */}
          <div className="mt-4" aria-labelledby="donations-list-heading">
            <h4 id="donations-list-heading" className="h5 mb-3">
              Listado accesible ({donations.length} disponible{donations.length === 1 ? '' : 's'})
            </h4>
            <div className="row g-3" role="list">
              {donations.map((item) => {
                const isSelected = item.id === selectedId;
                const deadline = new Intl.DateTimeFormat('es-MX', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                  timeZone: 'America/Merida',
                }).format(new Date(item.pickup_deadline));

                const remaining = item.remaining_quantity || item.quantity;

                return (
                  <div
                    key={item.id}
                    className="col-md-6"
                    role="listitem"
                    ref={(el) => {
                      cardRefs.current[item.id] = el;
                    }}
                  >
                    <article
                      className={`card h-100 shadow-sm border ${
                        isSelected ? 'donation-card-selected' : ''
                      }`}
                    >
                      <div className="card-body d-flex flex-column">
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <h5 className="card-title h6 mb-0 text-success fw-bold">
                            {item.title}
                          </h5>
                          <span className="badge bg-secondary ms-2">
                            {categoryLabels[item.food_category] || item.food_category}
                          </span>
                        </div>

                        <p className="card-text small text-muted mb-2">
                          {item.description}
                        </p>

                        <div className="mb-2">
                          <span className="badge text-bg-light border me-2">
                            📦 Disponibles: {formatQuantity(remaining, item.unit)}
                          </span>
                          <span className="badge text-bg-warning text-dark">
                            ⏰ Límite: {deadline}
                          </span>
                        </div>

                        <div className="small text-muted mb-3 mt-auto">
                          <div>
                            <strong>Punto de recogida:</strong> {item.pickup?.pickup_label}
                          </div>
                          <div>
                            <strong>Comercio:</strong> {item.pickup?.display_name}
                          </div>
                        </div>

                        <div className="d-flex gap-2">
                          <button
                            type="button"
                            className="btn btn-outline-success btn-sm flex-fill"
                            onClick={() => setSelectedId(item.id)}
                            aria-label={`Ubicar ${item.title} en el mapa`}
                          >
                            📍 Ver en mapa
                          </button>
                          <button
                            type="button"
                            className="btn btn-success btn-sm flex-fill"
                            disabled={detailLoading}
                            onClick={() => openDetail(item)}
                            aria-label={`Ver información y solicitar reserva de ${item.title}`}
                          >
                            Ver detalle y reservar
                          </button>
                        </div>
                      </div>
                    </article>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
