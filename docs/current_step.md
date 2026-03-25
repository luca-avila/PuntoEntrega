# PR D - Backend Product Requests

## 1) Objetivo del PR

Implementar la feature de solicitudes de productos en backend sobre el modelo owner/member ya vigente:

- Un `member` puede crear una solicitud de producto para su organización.
- El backend persiste la solicitud y notifica por email al owner.
- El owner puede auditar solicitudes desde un listado.

Este PR debe dejar product requests funcionales de punta a punta en backend (persistencia + reglas + API + email/background + tests), sin incluir cambios de frontend.

## 2) Alcance exacto (in scope)

- Nueva tabla `product_requests` con migración Alembic.
- Nueva feature `backend/features/product_requests/` (`models`, `schemas`, `service`, `email`, `api/routes`, `wiring`).
- Endpoint de creación para `member`: `POST /product-requests`.
- Endpoint de listado para `owner`: `GET /product-requests`.
- Envío de email al owner en background con estado/reintentos.
- Tests backend completos de permisos, reglas y estados de email.

## 3) Fuera de alcance (out of scope)

- Cambios frontend/UI de solicitud.
- Cambios de invitaciones (ya cubiertos en PR C).
- Nuevos roles/permisos más allá de owner/member.
- Automatizaciones externas adicionales (colas, workers dedicados, etc.).

## 4) Cambios técnicos detallados

### 4.1 Migración Alembic

Crear una nueva migración:

- `backend/alembic/versions/0005_create_product_requests.py`

Tabla `product_requests`:

1. `id` UUID PK.
2. `organization_id` UUID FK -> `organizations.id` (ondelete=`CASCADE`, index).
3. `requested_by_user_id` UUID FK -> `user.id` (ondelete=`RESTRICT`, index).
4. `subject` string(255), obligatorio.
5. `message` text/string largo, obligatorio.
6. `email_status` enum/string: `pending|sent|failed` (index).
7. `email_attempts` int default 0.
8. `email_last_error` text nullable.
9. `email_sent_at` datetime tz nullable.
10. `created_at`, `updated_at`.

Compatibilidad:
- Mantener soporte SQLite en tests.

### 4.2 Modelo SQLAlchemy

Crear `backend/features/product_requests/models.py` con:

- Enum `ProductRequestEmailStatus`.
- Modelo `ProductRequest` con campos y relaciones mínimas (`organization`, `requested_by_user`).

Actualizar `backend/features/models_registry.py` para registrar el módulo nuevo.

### 4.3 Schemas Pydantic

Crear `backend/features/product_requests/schemas.py`:

1. `ProductRequestCreate`
   - `subject` obligatorio, max 255.
   - `message` obligatorio, mínimo razonable (ej. 10 chars), trim.

2. `ProductRequestRead`
   - incluir ids clave, `subject`, `message`, `email_status`, `email_attempts`, `email_last_error`, `email_sent_at`, `created_at`.

3. `ProductRequestListFilters` (opcional si necesitás filtros simples por status/fecha).

### 4.4 Servicio de product requests

Crear `backend/features/product_requests/service.py` con casos de uso explícitos:

1. `create_product_request(...)`
   - Requiere usuario autenticado perteneciente a organización.
   - Solo `member` puede crear; `owner` recibe `403`.
   - Persiste la request en estado `pending`.
   - Commit antes de disparar email.

2. `list_product_requests_for_organization(...)`
   - Solo `owner`.
   - Orden recomendado: más nuevas primero.

3. `send_product_request_email_in_background(...)`
   - Patrón equivalente a deliveries:
     - reintentos acotados (`EMAIL_SEND_MAX_ATTEMPTS`)
     - delay entre intentos
     - termina en `sent` o `failed`
   - Resolver owner desde `organizations.owner_user_id`.
   - Enviar solo si owner está activo y verificado.
   - Si no hay owner enviable: marcar `failed` con error explícito.
   - Guardar `email_attempts`, `email_last_error`, `email_sent_at`.

Regla crítica:
- Si el envío falla, la solicitud NO se pierde: debe quedar persistida con estado final consistente.

### 4.5 Email de solicitud

Crear `backend/features/product_requests/email.py`:

- Reusar infraestructura de email existente (Resend + config actual).
- Subject sugerido: `"Nueva solicitud de producto - {organization_name}"`.
- Body con: organización, requester email, asunto, mensaje, fecha.

### 4.6 API Routes + Wiring

Crear `backend/features/product_requests/api/routes.py`:

1. `POST /product-requests` (member)
2. `GET /product-requests` (owner)

Integración:
- `backend/features/product_requests/wiring.py`
- Montar router en `backend/app/api.py` (tag `product-requests`).

Handlers finos:
- validan payload/dependencias
- delegan reglas al service
- disparan background task desde router (`BackgroundTasks`)

## 5) Ajustes de tests backend

Crear `backend/tests/test_product_requests.py` con cobertura mínima:

1. `member` puede crear request (`201`).
2. `owner` no puede crear request (`403`).
3. no autenticado recibe `401` en creación/listado protegidos.
4. `owner` puede listar requests de su organización.
5. `member` no puede listar requests (`403`).
6. creación persiste request con `email_status=pending` antes del envío.
7. envío exitoso marca `sent`, incrementa intentos y setea `email_sent_at`.
8. falla de envío termina en `failed` y conserva request.
9. si owner no enviable (inactivo/no verificado/sin email válido), queda `failed`.
10. aislamiento multi-tenant en listado y creación.

## 6) Verificación y checks del PR

Ejecutar:

1. `cd backend && uv run alembic upgrade head`
2. `cd backend && uv run pytest -q`
3. Smoke manual:
   - member crea request
   - owner lista requests
   - validar transición de email `pending -> sent|failed`

## 7) Riesgos y mitigaciones

Riesgo: acoplar creación al envío y perder solicitudes cuando falla email.
- Mitigación: persistir y commitear request antes del envío en background.

Riesgo: estados inconsistentes por reintentos concurrentes.
- Mitigación: guardas de idempotencia y actualización de estado en un único flujo.

Riesgo: envío a owner inválido (inactivo/no verificado).
- Mitigación: validar destinatario antes de enviar y registrar motivo de `failed`.

## 8) Criterios de aceptación del PR D

- Feature `product_requests` creada e integrada al app.
- `member` crea solicitudes correctamente.
- `owner` puede listar solicitudes de su organización.
- Envío de email corre en background con retries y estado final consistente.
- Si falla envío o no hay owner enviable, la request queda persistida con `failed`.
- Suite backend en verde.

## 9) Secuencia de implementación sugerida (orden interno)

1. Migración + modelo `ProductRequest`.
2. Schemas y servicio de reglas core (crear/listar).
3. Email + background sender con retries.
4. API routes + wiring.
5. Tests completos de product requests.
6. Run tests + smoke final.
