# Modelo de datos propuesto

| Entidad | Campos esenciales |
|---|---|
| User | id, email único, password_hash, role, created_at |
| RestaurantProfile | user_id, display_name, contact, pickup_lat, pickup_lng |
| BeneficiaryApplication | id, user_id, answers_json, consent_at, status, submitted_at |
| ApplicationReview | id, application_id, reviewer_id, decision, reason, reviewed_at |
| Donation | id, restaurant_id, title, description, quantity, unit, food_category, allergens, storage_notes, prepared_at, pickup_deadline, status, created_at |
| DonationRequest | id, donation_id, beneficiary_id, status, requested_at, confirmed_at |
| Appeal | id, application_id, message, status, created_at |

## Consideraciones
- Fase 5: `restaurant_profiles` usa `user_id` como clave y almacena nombre, contacto, referencia, latitud/longitud y versión. `donations` almacena campos alimentarios, `quantity_milli` entero, unidad, copia de recogida, fecha de confirmación de datos simulados, fechas UTC y versión. Estados persistidos disponible/cancelada; vencida se calcula con la hora del servidor. Las solicitudes parciales se añaden en fase 7.
- Fase 4: `application_reviews` guarda revisor, versión revisada, decisión, motivo y fecha. `appeals` guarda mensaje, estado pendiente/resuelto y referencia a la decisión de resolución. Las operaciones de revisión y apelación actualizan la versión de la solicitud dentro de la misma transacción. Historial y apelaciones se eliminan en cascada ORM cuando se elimina una solicitud editable.
- Fase 2: User se persiste en `users`, con `restaurant_authorized` (falso por defecto) y `session_token` anulable para revocación. El rol está restringido por CHECK.
- Fase 3: BeneficiaryApplication se persiste en `beneficiary_applications`, única por `user_id`. Añade `consent_version`, `updated_at` y `version` para evitar actualizaciones perdidas. Estados `draft`, `pending`, `information_requested`, `approved`, `rejected`; el beneficiario solo puede producir borrador o pendiente. Las decisiones serán parte de fase 4. Fechas en UTC y presentación en America/Merida.
- Acuerdo posterior: reservas parciales. DonationRequest incluirá cantidad solicitada; Donation distinguirá cantidad total, reservada y entregada. Definir precisión por unidad antes de implementar. Confirmar reserva existencias; entregar mueve reservado a entregado sin doble descuento.
- Restringir acceso a `answers_json` a la persona titular y revisores autorizados.
- Definir periodo de retención y borrado de encuestas.
- Impedir que dos solicitudes confirmen la misma unidad disponible sin control transaccional.
- Usar migraciones cuando evolucione el esquema.
