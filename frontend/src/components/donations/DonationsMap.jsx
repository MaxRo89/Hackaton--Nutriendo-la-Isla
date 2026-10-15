import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

function MapController({ selectedDonation }) {
  const map = useMap();
  useEffect(() => {
    if (selectedDonation?.pickup?.pickup_lat != null && selectedDonation?.pickup?.pickup_lng != null) {
      map.flyTo([selectedDonation.pickup.pickup_lat, selectedDonation.pickup.pickup_lng], 15, {
        duration: 1,
      });
    }
  }, [selectedDonation, map]);
  return null;
}

function createPinIcon(isSelected) {
  return L.divIcon({
    className: 'custom-map-pin-wrapper',
    html: `<div class="custom-map-pin ${isSelected ? 'active' : ''}" aria-hidden="true"><span>🍽️</span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -28],
  });
}

const DEFAULT_CENTER = [18.65, -91.8];
const DEFAULT_ZOOM = 13;

export default function DonationsMap({ donations, selectedId, onSelectDonation, onOpenDetail }) {
  const selectedDonation = donations.find((item) => item.id === selectedId);

  return (
    <div className="card border-0 shadow-sm mb-4">
      <div className="card-header bg-white py-3">
        <h4 className="h6 mb-0 text-success fw-bold">Mapa de puntos de recogida (OpenStreetMap)</h4>
        <small className="text-muted">
          Puntos aproximados de comercios donantes. No se muestran domicilios ni ubicación de personas beneficiarias.
        </small>
      </div>
      <div className="card-body p-0">
        <div className="donations-map-container" role="region" aria-label="Mapa interactivo de donaciones disponibles">
          <MapContainer
            center={DEFAULT_CENTER}
            zoom={DEFAULT_ZOOM}
            minZoom={11}
            maxZoom={19}
            scrollWheelZoom={false}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />
            <MapController selectedDonation={selectedDonation} />
            {donations.map((item) => {
              if (item.pickup?.pickup_lat == null || item.pickup?.pickup_lng == null) return null;
              const isSelected = item.id === selectedId;
              const deadline = new Intl.DateTimeFormat('es-MX', {
                dateStyle: 'short',
                timeStyle: 'short',
                timeZone: 'America/Merida',
              }).format(new Date(item.pickup_deadline));

              return (
                <Marker
                  key={item.id}
                  position={[item.pickup.pickup_lat, item.pickup.pickup_lng]}
                  icon={createPinIcon(isSelected)}
                  eventHandlers={{
                    click: () => onSelectDonation(item.id),
                  }}
                >
                  <Popup>
                    <div className="p-1">
                      <h5 className="h6 mb-1 fw-bold">{item.title}</h5>
                      <p className="small mb-1 text-muted">
                        <strong>Comercio:</strong> {item.pickup.display_name}
                      </p>
                      <p className="small mb-1">
                        <strong>Cantidad:</strong> {item.quantity} {item.unit}
                      </p>
                      <p className="small mb-1">
                        <strong>Recogida:</strong> {item.pickup.pickup_label}
                      </p>
                      <p className="small mb-2 text-danger">
                        <strong>Límite:</strong> {deadline}
                      </p>
                      <button
                        type="button"
                        className="btn btn-sm btn-success w-100"
                        onClick={() => onOpenDetail(item)}
                      >
                        Ver detalle completo
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
