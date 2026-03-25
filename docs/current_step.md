# PR C - Backend Invitations

## 1) Objetivo del PR

Implementar la feature de invitaciones de miembros por email en backend sobre el modelo owner/member ya existente:

- El owner invita por email a usuarios para sumarse a su organización.
- La invitación se acepta con token seguro y expiración.
- Debe soportar aceptación con cuenta nueva y con cuenta existente autenticada.

Este PR debe dejar invitaciones funcionales de punta a punta en backend (persistencia + reglas + API + email), sin incluir todavía product requests ni cambios de frontend.

## 2) Alcance exacto (in scope)

- Nueva tabla `organization_invitations` con migración Alembic.
- Nueva feature `backend/features/invitations/` (`models`, `schemas`, `service`, `email`, `api/routes`, `wiring`).
- Endpoints owner para crear/listar/cancelar invitaciones.
- Endpoints públicos/auth para validar y aceptar invitaciones.
- Envío de email de invitación reutilizando infraestructura de email existente.
- Tests backend completos de reglas de negocio y seguridad.

## 3) Fuera de alcance (out of scope)

- Product requests.
- Cambios de permisos adicionales fuera de invitaciones.
- Flujo frontend/UI de aceptación.
- Co-owners o permisos granulares avanzados.

## 4) Cambios técnicos detallados

### 4.1 Migración Alembic

Crear una nueva migración, por ejemplo:

- `backend/alembic/versions/0004_create_organization_invitations.py`

Tabla `organization_invitations`:

1. `id` UUID PK.
2. `organization_id` UUID FK -> `organizations.id` (ondelete=`CASCADE`, index).
3. `invited_email` string(320), normalizado lower-case (index).
4. `invited_by_user_id` UUID FK -> `user.id` (ondelete=`RESTRICT`, index).
5. `token_hash` string (no guardar token plano).
6. `status` enum/string: `pending|accepted|expired|cancelled` (index).
7. `expires_at` datetime tz (index recomendado).
8. `accepted_at` datetime tz nullable.
9. `created_at`, `updated_at`.

Regla funcional:
- Para `organization_id + invited_email`, solo una invitación `pending` activa a la vez.
- Si se vuelve a invitar y existe `pending`, se reutiliza registro, se renueva token y expiración.

Compatibilidad:
- Mantener soporte SQLite en tests.

### 4.2 Modelo SQLAlchemy

Crear `backend/features/invitations/models.py` con:

- Modelo `OrganizationInvitation`.
- Enum/constante de estado de invitación.
- Relaciones mínimas a organización y usuario invitador.

Actualizar `backend/features/models_registry.py` para registrar el nuevo módulo.

### 4.3 Schemas Pydantic

Crear `backend/features/invitations/schemas.py`:

1. Request owner create:
   - `OrganizationInvitationCreate` (`email`).

2. Read owner list:
   - `OrganizationInvitationRead` (id, invited_email, status, expires_at, accepted_at, created_at, invited_by_user_id).

3. Accept info público:
   - `OrganizationInvitationAcceptInfoRead` (estado de validez, organización mínima, email invitado, expiración).

4. Accept cuenta nueva:
   - `OrganizationInvitationAcceptCreate` (`token`, `password`, `password_confirm` si ya usan confirmación).

5. Accept autenticado:
   - `OrganizationInvitationAcceptAuthenticated` (`token`).

### 4.4 Servicio de invitaciones

Crear `backend/features/invitations/service.py` con casos de uso explícitos:

1. `create_or_resend_invitation(...)`
   - Requiere owner.
   - Normaliza email a lower-case.
   - Valida conflictos:
     - si email pertenece a usuario de otra organización -> `409`.
     - si pertenece a usuario de la misma organización -> `409`.
   - Si hay pending existente (org+email): reutiliza, renueva token+expires_at, estado `pending`.
   - Si no hay pending: crea invitación nueva.
   - Token seguro (secreto), persistir solo hash.
   - Commit atómico.

2. `list_invitations_for_organization(...)`
   - Owner.

3. `cancel_invitation(...)`
   - Owner.
   - Solo pending de su organización.
   - Pasa a `cancelled`.

4. `get_accept_info(token)`
   - Público.
   - Resuelve por hash.
   - Detecta inválido/expirado/cancelado/aceptado.

5. `accept_invitation_new_account(token, password, ...)`
   - Público.
   - Token válido y pending.
   - Crea usuario con `organization_id` de la invitación.
   - Marca usuario `is_verified = true`.
   - Marca invitación `accepted` + `accepted_at`.
   - Operación atómica.

6. `accept_invitation_authenticated(token, current_user)`
   - Usuario autenticado.
   - Email del usuario logueado debe coincidir con `invited_email`.
   - Usuario debe tener `organization_id IS NULL`.
   - Marca usuario dentro de la organización.
   - Marca invitación `accepted` + `accepted_at`.
   - Operación atómica.

Config:
- Expiración configurable (default 72h).

### 4.5 Email de invitación

Crear `backend/features/invitations/email.py`:

- Reusar proveedor/config de email ya usado en auth.
- Construir link: `${FRONTEND_URL}/aceptar-invitacion?token=...`.
- Enviar en creación/reenvío.

### 4.6 API Routes + Wiring

Crear `backend/features/invitations/api/routes.py`:

1. `POST /organization-invitations` (owner)
2. `GET /organization-invitations` (owner)
3. `POST /organization-invitations/{invitation_id}/cancel` (owner)
4. `GET /organization-invitations/accept-info?token=...` (público)
5. `POST /organization-invitations/accept` (público, cuenta nueva)
6. `POST /organization-invitations/accept-authenticated` (autenticado)

Agregar `backend/features/invitations/wiring.py` y montar router en `backend/app/api.py`.

Mantener handlers finos:
- Validan payload/dependencias.
- Delegan negocio al service.

## 5) Ajustes de tests backend

Crear `backend/tests/test_invitations.py` con cobertura mínima:

1. Owner puede invitar (`201`).
2. Member no puede invitar/listar/cancelar (`403`).
3. No autenticado recibe `401` en endpoints protegidos.
4. Si ya existe pending para email+org -> reutiliza invitación y reenvía (sin duplicar pending).
5. No permite invitar email de usuario en otra organización (`409`).
6. No permite invitar email ya miembro de la misma organización (`409`).
7. `accept-info` responde válido para token vigente.
8. `accept-info` responde inválido/expirado/cancelado/aceptado según estado.
9. Aceptación cuenta nueva crea usuario en org correcta y marca invitación `accepted`.
10. Aceptación autenticada exige email coincidente y usuario sin organización.
11. Token no puede reutilizarse después de aceptar.

## 6) Verificación y checks del PR

Ejecutar:

1. `cd backend && uv run alembic upgrade head`
2. `cd backend && uv run pytest -q`
3. Smoke manual:
   - owner invita email
   - listar invitaciones
   - `accept-info` con token
   - aceptar invitación (new account)
   - validar que invitación queda `accepted`

## 7) Riesgos y mitigaciones

Riesgo: vulnerabilidad por token plano o validación insuficiente.
- Mitigación: persistir solo hash, comparar de forma segura, validar estado/expiración en un único punto.

Riesgo: inconsistencias al aceptar invitación.
- Mitigación: aceptar con transacción atómica (usuario + invitación).

Riesgo: duplicación de invitaciones pending.
- Mitigación: regla de unicidad funcional y lógica de reutilización.

## 8) Criterios de aceptación del PR C

- Feature `invitations` creada e integrada al app.
- Owner puede crear/listar/cancelar invitaciones.
- Aceptación pública y autenticada funcionan según reglas.
- Invitaciones usan token hasheado y expiración.
- Reenvío reutiliza pending existente para `organization + email`.
- Suite backend en verde.

## 9) Secuencia de implementación sugerida (orden interno)

1. Migración + modelo `OrganizationInvitation`.
2. Schemas y servicio (reglas core).
3. Email y construcción de link.
4. API routes + wiring.
5. Tests completos de invitaciones.
6. Run tests + smoke final.
