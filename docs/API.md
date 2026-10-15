# API implementada — fase 7

## GET /api/health

Público, sin datos personales. Ejecuta `SELECT 1` en SQLite.

- 200: `{"status":"ok","database":"ok"}`.
- 503: `{"status":"unavailable","database":"unavailable"}`.

No certifica que las migraciones estén al día. Los errores HTTP se devuelven como JSON con `error.code` y `error.message`.

## Autenticación

| Método y ruta | Comportamiento |
|---|---|
| GET `/api/auth/csrf` | Devuelve `csrf_token` y establece la cookie de sesión anónima. |
| POST `/api/auth/register` | JSON `email`, `password`, `role` (`restaurant` o `beneficiary`); devuelve `user`, código 201 e inicia sesión. |
| POST `/api/auth/login` | JSON `email`, `password`; devuelve `user` e inicia sesión. |
| GET `/api/auth/me` | Cuenta actual o 401. No devuelve contraseña ni identificador de sesión. |
| POST `/api/auth/logout` | Revoca sesión en SQLite, limpia cookie y responde 204; requiere sesión. |
| GET `/api/restaurant/access` | Solo restaurante autorizado. |
| GET `/api/beneficiary/access` | Solo beneficiario; informa del flujo de solicitud. No habilita donaciones. |
| GET `/api/reviewer/access` | Solo revisor interno. |

Cada POST exige cookie y encabezado `X-CSRFToken`, obtenido de `/auth/csrf`. Renovarlo después de login, registro o logout; el cliente obtiene uno antes de cada escritura. CSRF inválido devuelve 400 con `error.code="csrf"`. No se reintentan escrituras automáticamente.

Correo normalizado a minúsculas, contraseña de 12–128 caracteres con hash scrypt. Campos extra y roles no públicos se rechazan. Registro duplicado: 409. Credenciales incorrectas: 401 con mensaje genérico. Rol o autorización insuficientes: 403. La autorización se consulta en SQLite en cada petición. Respuestas con `Cache-Control: no-store`.

Los endpoints `/access` verifican permisos y devuelven un mensaje; no implementan operaciones de fases posteriores. Las rutas de donaciones y revisión de ARQUITECTURA.md siguen siendo propuestas.

## Solicitud propia (solo beneficiario)

- `GET /api/applications/me`: devuelve `application` (null si no existe) y `consent_version` vigente.
- `POST /api/applications/me`: guarda o envía, con JSON `answers`, `action` (`save` o `submit`), `consent: true`, `consent_version` y `version` (0 para crear; después la versión recibida). Responde 200 con la solicitud persistida.
- `DELETE /api/applications/me`: JSON `version`. Elimina la solicitud editable y sus respuestas; conserva la cuenta. Responde 204.

POST y DELETE requieren CSRF. El usuario se obtiene de la sesión: no se acepta `user_id`, `status`, fechas ni otras propiedades administrativas. No existe acceso a solicitudes mediante un ID ajeno para beneficiarios. Roles restaurante/revisor reciben 403 en estas rutas; revisión tiene endpoints propios protegidos.

`answers`: `zone`, `availability`, `economic_context` (texto); `household_size` (entero 1–100 o null); `frequency` (`occasional`, `weekly`, `daily`); `transport` (`yes`, `limited`, `no`); `refrigeration` (`yes`, `no`). Los campos opcionales pueden omitirse; opciones vacías significan no responder. Solo enviar exige zona y disponibilidad no vacías.

Guardar produce `draft` y limpia `submitted_at`; enviar produce `pending` y fecha de envío. El consentimiento registra fecha de servidor y versión del aviso. Versión desactualizada o solicitud ya revisada: 409. Validación inválida: 400, sin persistir respuestas. No hay aprobación automática.

## Revisión humana y apelación

- `GET /api/reviewer/applications`: solo revisor. Lista solicitudes enviadas (excluye borradores) con respuestas, `reviews` y `appeals`.
- `PATCH /api/reviewer/applications/:id`: solo revisor; JSON `version`, `decision` (`approved`, `rejected`, `information_requested`) y `reason` (1–1000 caracteres no vacíos). Solo admite solicitudes pendientes o rechazadas con apelación pendiente. Registra autor, fecha y versión revisada; el motivo es visible para el titular.
- `POST /api/applications/me/appeals`: solo beneficiario; JSON `version`, `message` (1–1000 caracteres no vacíos). Solo solicitud propia rechazada sin apelación pendiente. Responde 201 con solicitud actualizada; no cambia la decisión anterior.

Escrituras con CSRF, autorización y versionado. Una nueva decisión resuelve la apelación y guarda `resolution_review_id` en la misma transacción. No existen endpoints para editar el historial. Aclaraciones permiten corregir y reenviar. La eliminación permitida de una solicitud editable borra también revisiones y apelaciones asociadas en la demo, sin dejar textos privados huérfanos.

## Restaurantes y donaciones

- `GET /api/restaurant/profile`: perfil propio o null, solo restaurante.
- `PUT /api/restaurant/profile`: `display_name` (120), `contact` (200), `pickup_label` (200), coordenadas numéricas `pickup_lat`/`pickup_lng` y `version` (0 inicialmente). Retorna `profile`. Coordenadas finitas y en rango. No admite identificadores ajenos.
- `GET /api/restaurant/donations`: solo restaurante autorizado; devuelve únicamente donaciones propias.
- `POST /api/donations`: autorizado y con perfil completo. JSON `title` (120), `description` (1000), `quantity` como cadena decimal, `unit` (`pieza`, `porcion`, `kg`), `food_category` (`panaderia`, `envasado`, `preparada`, `fresco`), `allergens`, `storage_notes`, `handling_notes` (500 cada uno), `prepared_at` opcional, `pickup_deadline`, `safety_confirmed: true`. Fechas ISO con zona; comida preparada exige preparación. Respuesta 201 con `donation`.
- `POST /api/donations/:id/cancel`: autorizado y propietario, JSON `version`; solo vigente/disponible. Respuesta con donación cancelada, sin borrarla. ID ajeno: 404; versión o estado inválido: 409.

Todas las escrituras llevan CSRF. Cantidades positivas hasta 100000, enteras salvo kg (tres decimales); se almacenan como enteros escalados y se devuelven como cadena decimal. La respuesta incluye punto original de recogida y estado efectivo (`available`, `cancelled`, `expired`).

## Descubrimiento de donaciones (Fase 6)

- `GET /api/donations`: solo persona beneficiaria con solicitud aprobada (`status: "approved"`). Devuelve lista de donaciones vigentes y disponibles (`status: "available"` y `pickup_deadline` mayor que la hora actual del servidor en UTC). Excluye automáticamente donaciones canceladas y vencidas.
- `GET /api/donations/:id`: solo persona beneficiaria con solicitud aprobada. Devuelve la información completa de la donación identificada si está vigente y disponible. Donaciones canceladas, vencidas o inexistentes devuelven 404 (`error.code: 404`, mensaje descriptivo).

Ambos endpoints exigen sesión activa (401 si no hay sesión) y rol `beneficiary` con solicitud aprobada en el servidor (403 si el rol es restaurante/revisor o si la solicitud no está aprobada: borrador, pendiente, información solicitada, rechazada o inexistente).

Cada donación en la respuesta incluye:
- `id`, `title`, `description`, `food_category`, `unit`, `quantity` (cadena decimal formateada), `version`.
- `allergens`, `storage_notes`, `handling_notes`.
- `pickup_deadline`, `prepared_at` (si aplica), `created_at`, `safety_confirmed_at` (fechas ISO UTC).
- `pickup`: copia inmutable del punto de recogida tomada en el momento de la publicación (`display_name`, `contact`, `pickup_label`, `pickup_lat`, `pickup_lng`). No sustituida por cambios posteriores del restaurante.
- `status`: `"available"`.

## Solicitud y entrega de reservas (Fase 7)

- `POST /api/donations/:id/requests`: solo beneficiario aprobado. JSON `quantity` (cadena decimal) y `notes` opcional (hasta 500 caracteres). Requiere CSRF. Valida existencias disponibles en `quantity_milli`, unidad (enteras para pieza/porción, 3 decimales para kg) y que la donación esté vigente. Evita solicitudes duplicadas activas para la misma donación (409). Responde 201 con `request` en estado `"pending"`.
- `GET /api/beneficiary/requests`: solo beneficiario aprobado. Lista todas las solicitudes realizadas por la cuenta, con título de la donación, cantidad solicitada, notas, snapshot del punto de recogida y estado actual (`pending`, `confirmed`, `cancelled`, `rejected`).
- `POST /api/requests/:id/cancel`: solo beneficiario titular. JSON `version`. Requiere CSRF. Permite cancelar una solicitud en estado `"pending"`. Cambia su estado a `"cancelled"` y registra fecha de cancelación.
- `GET /api/restaurant/donations/:id/requests`: solo restaurante autorizado y propietario de la donación. Devuelve la lista de solicitudes recibidas para ese alimento.
- `POST /api/requests/:id/confirm`: solo restaurante autorizado propietario. JSON `version`. Requiere CSRF. Transaccional: valida que la donación esté vigente y que la cantidad solicitada no supere `remaining_milli`. Cambia el estado de la solicitud a `"confirmed"`, descuenta existencias disponibles y registra `confirmed_at`. Si las existencias llegan a 0, el estado efectivo de la donación cambia a `"exhausted"`.
- `POST /api/requests/:id/reject`: solo restaurante autorizado propietario. JSON `version`. Requiere CSRF. Cambia el estado de una solicitud pendiente a `"rejected"`, liberando la petición sin descontar existencias.

Reportes de seguridad y revisión administrativa de incidencias corresponden a la fase 8.
