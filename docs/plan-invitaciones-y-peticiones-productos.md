# Plan Detallado: Organización Manual + Invitaciones de Miembros + Petición de Productos

## 1. Objetivo

Definir un plan de implementación (sin tocar código todavía) para agregar:

1. Creación manual de organización desde la app (onboarding), eliminando la creación automática al registrarse.
2. Modelo de ownership con owner único por organización (sin `role` en `users`).
3. Invitaciones de miembros por email.
4. Ventana de petición de productos para miembros, enviando email al owner de la organización.

Este plan está alineado al stack actual:
- Backend: FastAPI + SQLAlchemy + Alembic + Resend.
- Frontend: React + TypeScript + Vite.
- Multi-tenant por `organization_id`.

---

## 2. Cambio de Dirección (respecto del plan anterior)

### 2.1 Decisiones cerradas

- La organización **no** se crea en `/auth/register`.
- El usuario se registra primero y luego crea organización manualmente en una pantalla de onboarding.
- `users.role` deja de ser relevante y se elimina del modelo/flujo del MVP.
- El owner de la organización se determina por `organizations.owner_user_id`.
- MVP con owner único.

### 2.2 Fuera de alcance

- Co-owners.
- Permisos avanzados por rol dentro de una misma organización.

Nota de evolución futura: si se necesitan co-owners, la extensión natural es una tabla de membresías/admins. No se agrega ahora para evitar complejidad prematura.

---

## 3. Estado Actual (base real)

- `users` tiene `organization_id` y `role`.
- `/auth/register` hoy crea organización automáticamente y setea `role = owner`.
- El aislamiento por organización está implementado en `locations`, `products`, `deliveries`.
- No existen módulos de invitaciones ni de peticiones de productos.
- No hay autorización owner/member explícita en endpoints actuales.

---

## 4. Diseño de Datos (Alembic + SQLAlchemy)

## 4.1 Ajustes en `users`

Objetivo: desacoplar ownership del usuario.

- Mantener `organization_id` nullable (usuario puede existir sin organización hasta completar onboarding).
- Eliminar columna `role`.
- Regla de negocio MVP: `1 usuario = 1 organización` (ya representado por una sola FK en `users`).

Estrategia de migración (etapa temprana, sin usuarios reales):
- No hacer backfill legacy de `role`.
- Si hay datos locales de pruebas que chocan con el nuevo esquema, resetear la DB local y aplicar migraciones desde cero.

## 4.2 Ajustes en `organizations`

Agregar:
- `owner_user_id` (UUID, FK a `user.id`, `nullable=False`).

Reglas:
- `owner_user_id` debe pertenecer a la misma organización (`users.organization_id == organizations.id`) a nivel aplicación.
- Owner único por organización.

Migración simplificada (sin retrocompatibilidad de datos productivos):
1. Agregar `owner_user_id` con FK.
2. Eliminar `users.role`.
3. Si la base local tiene datos viejos incompatibles, recrear esquema local y volver a correr `alembic upgrade head`.

## 4.3 Nueva tabla: `organization_invitations`

Campos:
- `id` (UUID, PK)
- `organization_id` (FK organizations, cascade delete)
- `invited_email` (string 320, lower-case)
- `invited_by_user_id` (FK user)
- `token_hash` (string)
- `status` (`pending|accepted|expired|cancelled`)
- `expires_at` (datetime tz)
- `accepted_at` (datetime tz nullable)
- `created_at`, `updated_at`

Índices:
- `organization_id`
- `invited_email`
- `status`

Regla de unicidad funcional:
- Para `email + organization`, solo una invitación activa (`pending`) a la vez.
- Si ya existe `pending`, se reutiliza y se reenvía (renovando token y vencimiento).

## 4.4 Nueva tabla: `product_requests`

Campos:
- `id` (UUID, PK)
- `organization_id` (FK organizations, cascade delete)
- `requested_by_user_id` (FK user)
- `requested_by_email` (snapshot)
- `subject` (string 255)
- `message` (text)
- `email_status` (`pending|sent|failed`)
- `created_at`, `updated_at`

Índices:
- `organization_id`
- `requested_by_user_id`
- `created_at`

---

## 5. Backend: Arquitectura y Casos de Uso

Crear dos features nuevas:
1. `features/invitations/`
2. `features/product_requests/`

Y extender `features/organizations/` para onboarding y ownership.

Estructura recomendada por feature:
- `models.py`
- `schemas.py`
- `service.py`
- `email.py` (si aplica)
- `api/routes.py`
- `wiring.py`

Actualizar:
- `features/models_registry.py`
- `app/api.py`

## 5.1 Dependencias de autorización

Agregar dependencias reutilizables en `features/organizations/service.py`:
- `get_current_user_with_optional_organization`
- `get_current_user_with_organization`
- `require_organization_owner`
- `require_organization_member` (miembro no-owner)
- `require_organization_user` (owner o member)

Definición de owner:
- `organization.owner_user_id == current_user.id`.

Definición de member:
- usuario autenticado con `organization_id` y que no es owner.

## 5.2 Onboarding de organización (backend)

### Endpoints

- `POST /organizations`
  - autenticado, `current_user.organization_id IS NULL`
  - crea organización manualmente
  - asigna al usuario a esa organización
  - setea `organizations.owner_user_id = current_user.id`

- `GET /organizations/current`
  - autenticado con organización
  - devuelve metadata mínima: `id`, `name`, `slug`, `owner_user_id`

- `GET /organization-members`
  - owner
  - lista usuarios de su organización (email, activo, verificado, created info disponible)

### Reglas

- Usuario con organización no puede crear otra.
- La creación de organización y asignación del usuario deben ser atómicas en una transacción.
- Slug único generado con la estrategia actual.

## 5.3 Feature Invitaciones (backend)

### Endpoints

- `POST /organization-invitations` (owner)
- `GET /organization-invitations` (owner)
- `POST /organization-invitations/{invitation_id}/cancel` (owner)
- `GET /organization-invitations/accept-info?token=...` (público)
- `POST /organization-invitations/accept` (público, cuenta nueva)
- `POST /organization-invitations/accept-authenticated` (autenticado, cuenta existente)

### Reglas de negocio

- Validar email, normalizar a lower-case.
- No invitar si el email ya pertenece a un usuario de otra organización.
- Si ya pertenece a la misma organización: `409`.
- Si ya hay invitación `pending` para ese email+org: reutilizar y reenviar.
- Expiración configurable: 72h.
- Guardar solo hash del token.
- Token expirado/cancelado/aceptado: no aceptable.

### Aceptación

- Cuenta nueva:
  - crea usuario asociado a la org invitante
  - marca `is_verified = true` (token de invitación válido)
- Cuenta existente:
  - requiere login previo
  - email del usuario logueado debe coincidir con invitación
  - usuario debe tener `organization_id IS NULL`
  - asocia usuario a la org y marca invitación como aceptada

### Email de invitación

- Reutilizar infraestructura Resend.
- Link: `${FRONTEND_URL}/aceptar-invitacion?token=...`

## 5.4 Feature Product Requests (backend)

### Endpoints

- `POST /product-requests` (member)
- `GET /product-requests` (owner, auditoría)

### Reglas

- `subject` obligatorio (max 255)
- `message` obligatorio (mínimo razonable, ej. 10)
- Persistir request antes de enviar email
- Email recipient: owner único (`organizations.owner_user_id`), solo si está activo y verificado
- Si no hay owner enviable o falla envío: conservar request con `email_status=failed`

### Envío en background

Patrón equivalente al de `deliveries`:
- estado inicial `pending`
- retries acotados
- final `sent/failed`

## 5.5 Ajustes de permisos en endpoints existentes

Con owner único:
- `POST/PATCH` de `products`: solo owner
- `POST/PATCH` de `locations`: solo owner
- `POST` de `deliveries`: solo owner
- `GET` de recursos operativos: owner y member

---

## 6. Frontend: Pantallas y Flujo

## 6.1 Onboarding organización

Nueva pantalla protegida para usuarios sin organización:
- ruta sugerida: `/onboarding/organizacion`
- formulario: nombre de organización
- submit a `POST /organizations`
- éxito: refrescar sesión/contexto y redirigir a `/`

Regla global:
- si usuario autenticado tiene `organization_id = null`, redirigir a onboarding y bloquear el resto de rutas de negocio.

## 6.2 Gestión de equipo e invitaciones (owner)

Nueva ruta `/equipo`:
- listado de miembros
- formulario de invitación (email)
- listado de invitaciones con estado
- acción de cancelar

## 6.3 Aceptación de invitación (público)

Nueva página pública `/aceptar-invitacion`:
- lee token de query
- consulta `accept-info`
- flujo cuenta nueva: contraseña + confirmar
- flujo cuenta existente: pedir iniciar sesión y luego completar aceptación autenticada

## 6.4 Petición de productos (member)

En `/productos`:
- owner: mantiene botones de alta/edición
- member: ve acción `Solicitar producto`
- formulario simple (asunto + detalle) que llama `POST /product-requests`

## 6.5 Contratos frontend

Agregar:
- `src/api/contracts/invitations.ts`
- `src/api/contracts/product-requests.ts`
- `src/api/contracts/organizations.ts`
- `src/api/invitations-api.ts`
- `src/api/product-requests-api.ts`
- `src/api/organizations-api.ts`

Actualizar:
- `src/api/contracts/auth.ts` para remover `role`
- estado de auth/context para usar ownership desde `organizations/current`

---

## 7. Testing (criterios mínimos)

## 7.1 Backend

Nuevos tests:
- `backend/tests/test_organizations_onboarding.py`
- `backend/tests/test_invitations.py`
- `backend/tests/test_product_requests.py`

Cobertura clave:

Onboarding:
- register no crea organización
- usuario sin organización puede crearla manualmente
- usuario con organización no puede crear segunda
- owner_user_id se setea correctamente

Invitaciones:
- solo owner invita/lista/cancela
- member no puede invitar (403)
- no autenticado (401)
- token inválido/expirado/cancelado/reutilizado
- aceptación cuenta nueva
- aceptación cuenta existente autenticada
- aislamiento multi-tenant

Peticiones de productos:
- member crea request
- owner no puede crear request (403)
- no autenticado (401)
- owner puede listar requests
- email intenta enviarse al owner
- fallas de email persisten con `failed`

Regresiones:
- tests existentes de auth para ajustar expectativa: `organization_id` en registro pasa a `null`
- tests de permisos en products/locations/deliveries para owner/member

## 7.2 Frontend

- `npm run lint`
- `npm run build`
- QA manual:
  - registro -> onboarding -> creación org
  - owner invita
  - invitado acepta
  - member solicita producto
  - owner recibe email y ve historial

---

## 8. Orden de Implementación Recomendado (PRs)

1. **PR A - Modelo ownership + onboarding base**
   - migraciones (`organizations.owner_user_id`, drop `users.role`), ajuste register sin org automática, endpoint create org
2. **PR B - Authz por owner/member sin role**
   - nuevas dependencias de autorización + endurecer permisos en endpoints existentes
3. **PR C - Backend invitaciones**
   - models/schemas/service/routes/email + tests
4. **PR D - Backend product requests**
   - models/schemas/service/routes/email/background + tests
5. **PR E - Frontend onboarding + ownership context**
   - guard de rutas, pantalla crear organización
6. **PR F - Frontend equipo/invitaciones + aceptación pública + solicitud de productos**
7. **PR G - Documentación final y hardening**

Cada PR debe salir con tests y validación funcional del flujo completo.

---

## 9. Criterios de Aceptación de Negocio

- Un usuario nuevo se registra sin organización.
- Puede crear su organización manualmente desde la app y queda como owner único.
- El owner puede invitar miembros por email y gestionar estado de invitaciones.
- Un invitado puede aceptar y quedar asociado a la organización correcta.
- Un member puede solicitar productos desde frontend.
- El owner recibe email de la solicitud y puede auditar requests.
- Todo queda aislado por organización y protegido por backend.

---

## 10. Riesgos y Mitigaciones

- Riesgo: entorno local con datos previos al cambio de modelo.
  - Mitigación: tratar PR A como cambio de bootstrap y resetear DB local si es necesario.

- Riesgo: romper flujos por remover `role`.
  - Mitigación: actualizar en el mismo PR modelos, schemas, tests y contratos para que el cambio sea consistente punta a punta.

- Riesgo: usuarios autenticados sin organización accediendo rutas operativas.
  - Mitigación: bloqueo dual backend (403) + frontend (redirect onboarding).
